#!/usr/bin/env python3
# scripts/backtests/backtest_current_system.py
"""
回測現有系統（2020-2025）

買入：加權分數（MVRV 65% + RSI 25% + F&G 10%）
賣出：Pi Cycle Top + 綜合分數
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
    # RSI (日線)
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 200週 MA
    df['ma_200w'] = df['price'].rolling(window=1400).mean()
    
    # MVRV 代理
    df['mvrv'] = df['price'] / df['ma_200w']
    
    # Pi Cycle
    df['ma_111'] = df['price'].rolling(window=111).mean()
    df['ma_350'] = df['price'].rolling(window=350).mean()
    df['pi_cycle_signal'] = (df['ma_111'] > df['ma_350'] * 2)
    
    # F&G 模擬（簡化：基於價格動能）
    df['price_change_30d'] = df['price'].pct_change(30) * 100
    df['fg'] = 50 + df['price_change_30d'].clip(-50, 50)
    
    return df

def get_buy_multiplier(mvrv, rsi, fg):
    """計算買入倍數（加權分數）"""
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
    
    # 倍數
    if composite < 15:
        return 3.5
    elif composite < 25:
        return 2.0
    elif composite < 35:
        return 1.5
    elif composite < 50:
        return 1.0
    elif composite < 60:
        return 0.5
    else:
        return 0.0

def backtest():
    """回測"""
    print("\n📊 回測現有系統...")
    print("="*70)
    
    df = fetch_data()
    df = calculate_indicators(df)
    
    # 初始倉位
    core_btc = 0.0
    trade_btc = 0.0
    cash = INITIAL_CAPITAL
    total_invested = INITIAL_CAPITAL
    
    trades = []
    
    # 每週買入
    for i in range(1400, len(df), 7):  # 從 1400 天後開始（等指標穩定）
        row = df.iloc[i]
        
        if pd.isna(row['mvrv']) or pd.isna(row['rsi']):
            continue
        
        # 買入
        multiplier = get_buy_multiplier(row['mvrv'], row['rsi'], row['fg'])
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
                'multiplier': multiplier
            })
        
        # 賣出（Pi Cycle）
        if row['pi_cycle_signal'] and trade_btc > 0:
            sell_amount = trade_btc
            sell_value = sell_amount * row['price'] * (1 - TRADE_FEE)
            
            cash += sell_value
            trade_btc = 0
            
            trades.append({
                'date': row['date'],
                'type': 'SELL',
                'price': row['price'],
                'amount': sell_amount,
                'usd': sell_value,
                'multiplier': 0
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
    
    print(f"\n{'='*70}")
    print("💰 回測結果")
    print(f"{'='*70}\n")
    
    print(f"期間：{df.iloc[1400]['date'].date()} ~ {df.iloc[-1]['date'].date()}")
    print(f"起始價格：${df.iloc[1400]['price']:,.0f}")
    print(f"當前價格：${current_price:,.0f}")
    
    print(f"\n現有系統：")
    print(f"  總 BTC：{total_btc:.6f}")
    print(f"  核心倉：{core_btc:.6f} BTC")
    print(f"  交易倉：{trade_btc:.6f} BTC")
    print(f"  現金：${cash:,.0f}")
    print(f"  總價值：${total_value:,.0f}")
    print(f"  平均成本：${avg_cost:,.0f}/BTC")
    
    print(f"\nHODL 對比：")
    print(f"  HODL BTC：{hodl_btc:.6f}")
    print(f"  HODL 價值：${hodl_value:,.0f}")
    
    print(f"\n績效對比：")
    print(f"  系統 vs HODL：{(total_value - hodl_value) / hodl_value * 100:+.2f}%")
    print(f"  系統 ROI：{(total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100:+.1f}%")
    print(f"  HODL ROI：{(hodl_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100:+.1f}%")
    
    # 交易記錄
    print(f"\n{'='*70}")
    print(f"📋 交易記錄（共 {len(trades)} 筆）")
    print(f"{'='*70}\n")
    
    buy_trades = [t for t in trades if t['type'] == 'BUY']
    sell_trades = [t for t in trades if t['type'] == 'SELL']
    
    print(f"買入：{len(buy_trades)} 筆")
    print(f"賣出：{len(sell_trades)} 筆")
    
    if len(sell_trades) > 0:
        print(f"\n賣出記錄：")
        for t in sell_trades:
            print(f"  {t['date'].date()} | ${t['price']:>7,.0f} | {t['amount']:.6f} BTC → ${t['usd']:>10,.0f}")
    else:
        print(f"\n⚠️ 未觸發任何賣出")
    
    # 最後 10 筆買入
    print(f"\n最後 10 筆買入：")
    for t in buy_trades[-10:]:
        print(f"  {t['date'].date()} | ${t['price']:>7,.0f} | {t['amount']:.8f} BTC "
              f"| 倍數 {t['multiplier']:.1f}x | ${t['usd']:>6,.0f}")
    
    # 儲存完整記錄
    df_trades = pd.DataFrame(trades)
    output_file = 'scripts/backtests/reports/current_system_trades.csv'
    df_trades.to_csv(output_file, index=False)
    print(f"\n📄 完整交易記錄已儲存：{output_file}")
    
    return total_value, hodl_value, avg_cost

if __name__ == "__main__":
    print("="*70)
    print("📊 現有系統回測（2020-2025）")
    print("="*70)
    
    total_value, hodl_value, avg_cost = backtest()
    
    print(f"\n✅ 回測完成")
    print(f"系統價值：${total_value:,.0f}")
    print(f"HODL 價值：${hodl_value:,.0f}")
    print(f"平均成本：${avg_cost:,.0f}/BTC")
