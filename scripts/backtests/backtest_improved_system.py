#!/usr/bin/env python3
# scripts/backtests/backtest_improved_system.py
"""
回測改進系統（2020-2025）

買入：加權分數（MVRV 65% + RSI 25% + F&G 10%）
     + 牛市後期降低倍數

賣出：Pi Cycle Top + 綜合分數
     + RSI > 80 保底
     + 回調 >20% 確認
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

INITIAL_CAPITAL = 10000
WEEKLY_INVESTMENT = 250
CORE_RATIO = 0.4
TRADE_FEE = 0.001

def fetch_data():
    """獲取 2020-2025 數據"""
    print("📥 獲取數據...")
    
    exchange = ccxt.binance()
    start_date = datetime(2020, 1, 1)
    since = int(start_date.timestamp() * 1000)
    
    all_ohlcv = []
    current = since
    
    while current < int(datetime.now().timestamp() * 1000):
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=current, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        current = ohlcv[-1][0] + 86400000
        if len(ohlcv) < 1000:
            break
    
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['price'] = df['close']
    
    print(f"✅ 獲取完成：{len(df)} 天")
    return df[['date', 'price']]

def calculate_indicators(df):
    """計算指標"""
    # RSI (日線和月線)
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 月線 RSI (30天)
    gain_30 = (delta.where(delta > 0, 0)).rolling(window=30).mean()
    loss_30 = (-delta.where(delta < 0, 0)).rolling(window=30).mean()
    rs_30 = gain_30 / loss_30
    df['rsi_monthly'] = 100 - (100 / (1 + rs_30))
    
    # 200週 MA
    df['ma_200w'] = df['price'].rolling(window=1400).mean()
    
    # MVRV 代理
    df['mvrv'] = df['price'] / df['ma_200w']
    
    # ATH
    df['ath'] = df['price'].expanding().max()
    
    # Pi Cycle
    df['ma_111'] = df['price'].rolling(window=111).mean()
    df['ma_350'] = df['price'].rolling(window=350).mean()
    df['pi_cycle_signal'] = (df['ma_111'] > df['ma_350'] * 2)
    
    # F&G 模擬
    df['price_change_30d'] = df['price'].pct_change(30) * 100
    df['fg'] = 50 + df['price_change_30d'].clip(-50, 50)
    
    return df

def get_buy_multiplier(mvrv, rsi, fg, price, ath):
    """計算買入倍數（加權分數 + 牛市調整）"""
    # MVRV 分數
    if mvrv < 0.1:
        mvrv_score = 0
    elif mvrv < 1.0:
        mvrv_score = 10
    elif mvrv < 3.0:
        mvrv_score = 30
    elif mvrv < 5.0:
        mvrv_score = 50
    else:
        mvrv_score = 80
    
    rsi_score = rsi if not pd.isna(rsi) else 50
    fg_score = fg if not pd.isna(fg) else 50
    
    # 加權
    composite = (mvrv_score * 0.65) + (rsi_score * 0.25) + (fg_score * 0.10)
    
    # 基礎倍數
    if composite < 15:
        multiplier = 3.5
    elif composite < 25:
        multiplier = 2.0
    elif composite < 35:
        multiplier = 1.5
    elif composite < 50:
        multiplier = 1.0
    elif composite < 60:
        multiplier = 0.5
    else:
        multiplier = 0.0
    
    # 牛市後期調整
    if price > ath * 1.2:
        multiplier *= 0.5  # 減半
    if price > ath * 1.5:
        multiplier = 0.0  # 停止買入
    
    return multiplier

def backtest():
    """回測"""
    print("\n📊 回測改進系統...")
    print("="*70)
    
    df = fetch_data()
    df = calculate_indicators(df)
    
    # 初始倉位
    core_btc = 0.0
    trade_btc = 0.0
    cash = INITIAL_CAPITAL
    
    trades = []
    peak_price = 0
    
    # 每週買入
    for i in range(1400, len(df), 7):
        row = df.iloc[i]
        
        if pd.isna(row['mvrv']) or pd.isna(row['rsi']):
            continue
        
        # 更新峰值
        if row['price'] > peak_price:
            peak_price = row['price']
        
        # 買入
        multiplier = get_buy_multiplier(row['mvrv'], row['rsi'], row['fg'], row['price'], row['ath'])
        invest_amount = WEEKLY_INVESTMENT * multiplier
        
        if cash >= invest_amount and invest_amount > 0:
            btc_bought = (invest_amount * (1 - TRADE_FEE)) / row['price']
            core_btc += btc_bought * CORE_RATIO
            trade_btc += btc_bought * (1 - CORE_RATIO)
            cash -= invest_amount
            
            trades.append({
                'date': row['date'],
                'type': 'BUY',
                'price': row['price'],
                'amount': btc_bought,
                'usd': invest_amount,
                'multiplier': multiplier,
                'reason': f'Composite score'
            })
        
        # 賣出邏輯（多重觸發）
        if trade_btc > 0:
            sell_reason = None
            sell_pct = 0
            
            # 1. 月線 RSI > 80 → 賣 10%
            if row['rsi_monthly'] > 80 and not any(t['type'] == 'SELL' and 'RSI >80' in t['reason'] for t in trades):
                sell_pct = 0.10
                sell_reason = 'RSI >80'
            
            # 2. 月線 RSI > 85 → 賣 20%
            elif row['rsi_monthly'] > 85 and not any(t['type'] == 'SELL' and 'RSI >85' in t['reason'] for t in trades):
                sell_pct = 0.20
                sell_reason = 'RSI >85'
            
            # 3. 回調 > 20% → 賣 70%
            elif peak_price > 0:
                drawdown = (row['price'] - peak_price) / peak_price
                if drawdown < -0.20 and not any(t['type'] == 'SELL' and '回調 >20%' in t['reason'] for t in trades):
                    sell_pct = 0.70
                    sell_reason = f'回調 >20% (from ${peak_price:,.0f})'
            
            # 4. Pi Cycle（終極）
            elif row['pi_cycle_signal'] and not any(t['type'] == 'SELL' and 'Pi Cycle' in t['reason'] for t in trades):
                sell_pct = 1.0
                sell_reason = 'Pi Cycle Top'
            
            # 執行賣出
            if sell_pct > 0:
                sell_amount = trade_btc * sell_pct
                sell_value = sell_amount * row['price'] * (1 - TRADE_FEE)
                
                cash += sell_value
                trade_btc -= sell_amount
                
                trades.append({
                    'date': row['date'],
                    'type': 'SELL',
                    'price': row['price'],
                    'amount': sell_amount,
                    'usd': sell_value,
                    'multiplier': 0,
                    'reason': sell_reason
                })
    
    # 結果
    current_price = df.iloc[-1]['price']
    total_btc = core_btc + trade_btc
    btc_value = total_btc * current_price
    total_value = btc_value + cash
    
    # 平均成本
    total_buy_usd = sum(t['usd'] for t in trades if t['type'] == 'BUY')
    total_buy_btc = sum(t['amount'] for t in trades if t['type'] == 'BUY')
    avg_cost = total_buy_usd / total_buy_btc if total_buy_btc > 0 else 0
    
    # HODL 對比
    hodl_btc = INITIAL_CAPITAL / df.iloc[1400]['price']
    hodl_value = hodl_btc * current_price
    
    # 原系統對比
    original_value = 17310  # 從前一個回測
    
    print(f"\n{'='*70}")
    print("💰 回測結果對比")
    print(f"{'='*70}\n")
    
    print(f"期間：{df.iloc[1400]['date'].date()} ~ {df.iloc[-1]['date'].date()}")
    print(f"起始價格：${df.iloc[1400]['price']:,.0f}")
    print(f"當前價格：${current_price:,.0f}")
    
    print(f"\n{'策略':<15} {'總價值':>12} {'ROI':>8} {'vs HODL':>10}")
    print("-"*70)
    print(f"{'原系統':<15} ${original_value:>11,.0f} {(original_value-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>7.1f}% {(original_value-hodl_value)/hodl_value*100:>9.1f}%")
    print(f"{'改進系統':<15} ${total_value:>11,.0f} {(total_value-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>7.1f}% {(total_value-hodl_value)/hodl_value*100:>9.1f}%")
    print(f"{'HODL':<15} ${hodl_value:>11,.0f} {(hodl_value-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>7.1f}% {'0.0%':>10}")
    
    print(f"\n改進效果：")
    print(f"  vs 原系統：{(total_value - original_value) / original_value * 100:+.1f}%")
    print(f"  vs HODL：{(total_value - hodl_value) / hodl_value * 100:+.1f}%")
    
    print(f"\n改進系統詳細：")
    print(f"  總 BTC：{total_btc:.6f}")
    print(f"  核心倉：{core_btc:.6f} BTC")
    print(f"  交易倉：{trade_btc:.6f} BTC")
    print(f"  現金：${cash:,.0f}")
    print(f"  平均成本：${avg_cost:,.0f}/BTC")
    
    # 交易統計
    buy_trades = [t for t in trades if t['type'] == 'BUY']
    sell_trades = [t for t in trades if t['type'] == 'SELL']
    
    print(f"\n交易統計：")
    print(f"  買入：{len(buy_trades)} 筆")
    print(f"  賣出：{len(sell_trades)} 筆")
    
    if sell_trades:
        print(f"\n賣出記錄：")
        for t in sell_trades:
            print(f"  {t['date'].date()} | ${t['price']:>7,.0f} | {t['amount']:.6f} BTC → ${t['usd']:>10,.0f}")
            print(f"    原因：{t['reason']}")
    
    return total_value, hodl_value, trades

if __name__ == "__main__":
    print("="*70)
    print("📊 改進系統回測（2020-2025）")
    print("="*70)
    
    total_value, hodl_value, trades = backtest()
    
    print(f"\n✅ 回測完成")
