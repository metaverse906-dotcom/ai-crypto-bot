#!/usr/bin/env python3
# scripts/backtests/backtest_1_5x_ath.py
"""
回測 1.5x ATH 策略

使用 2020-2025 完整數據
驗證策略跨週期有效性
"""

import ccxt
import pandas as pd
from datetime import datetime

def fetch_historical_data():
    """獲取 2020-2025 數據"""
    print("📥 獲取 2020-2025 BTC 數據...")
    
    exchange = ccxt.binance()
    
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2026, 1, 4)
    
    since = int(start_date.timestamp() * 1000)
    all_ohlcv = []
    current = since
    
    while current < int(end_date.timestamp() * 1000):
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

def calculate_rsi(prices, period=30):
    """計算月線 RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_1_5x_ath(df):
    """回測 1.5x ATH 策略"""
    print("\n📊 回測 1.5x ATH 策略...")
    print("="*70)
    
    initial_btc = 1.0
    core_ratio = 0.4
    
    core_btc = initial_btc * core_ratio
    trade_btc = initial_btc * (1 - core_ratio)
    cash = 0.0
    
    # 計算 RSI
    df['rsi'] = calculate_rsi(df['price'], period=30)
    
    # 追蹤 ATH
    df['ath'] = df['price'].expanding().max()
    df['ath_1_5x'] = df['ath'] * 1.5
    
    # 計算年初價格（rolling year）
    df['year_start_price'] = df['price'].shift(365)
    df['ytd_return'] = (df['price'] - df['year_start_price']) / df['year_start_price']
    
    sells = []
    sold_layers = set()
    peak_price = 0
    
    for idx, row in df.iterrows():
        if trade_btc <= 0:
            continue
        
        # 更新峰值
        if row['price'] > peak_price:
            peak_price = row['price']
        
        # 層 1：1.5x ATH 或年漲幅 >150% 或 RSI >80
        if 'layer1' not in sold_layers:
            trigger_15x = row['price'] >= row['ath_1_5x']
            trigger_ytd = row['ytd_return'] > 1.5 if not pd.isna(row['ytd_return']) else False
            trigger_rsi = row['rsi'] > 80 if not pd.isna(row['rsi']) else False
            
            if trigger_15x or trigger_ytd or trigger_rsi:
                sell_amount = initial_btc * (1 - core_ratio) * 0.15
                sell_value = sell_amount * row['price']
                
                cash += sell_value
                trade_btc -= sell_amount
                sold_layers.add('layer1')
                
                trigger_reason = []
                if trigger_15x:
                    trigger_reason.append('1.5x ATH')
                if trigger_ytd:
                    trigger_reason.append('YTD >150%')
                if trigger_rsi:
                    trigger_reason.append('RSI >80')
                
                sells.append({
                    'date': row['date'],
                    'layer': 1,
                    'price': row['price'],
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': ' + '.join(trigger_reason)
                })
                peak_price = row['price']
        
        # 層 2：從層 1 又漲 >30% 或 RSI >85
        if 'layer1' in sold_layers and 'layer2' not in sold_layers:
            if len(sells) > 0:
                layer1_price = sells[0]['price']
                trigger_gain = row['price'] >= layer1_price * 1.3
                trigger_rsi = row['rsi'] > 85 if not pd.isna(row['rsi']) else False
                
                if trigger_gain or trigger_rsi:
                    sell_amount = trade_btc * 0.294  # 25% of original trade position
                    sell_value = sell_amount * row['price']
                    
                    cash += sell_value
                    trade_btc -= sell_amount
                    sold_layers.add('layer2')
                    
                    sells.append({
                        'date': row['date'],
                        'layer': 2,
                        'price': row['price'],
                        'btc': sell_amount,
                        'value': sell_value,
                        'reason': '+30% from L1' if trigger_gain else 'RSI >85'
                    })
        
        # 層 3：回調 >20% 或 RSI 跌破 70
        if len(sold_layers) > 0 and 'layer3' not in sold_layers:
            drawdown = (row['price'] - peak_price) / peak_price
            trigger_drawdown = drawdown < -0.20
            trigger_rsi = (row['rsi'] < 70 and peak_price > row['price'] * 1.2) if not pd.isna(row['rsi']) else False
            
            if trigger_drawdown or trigger_rsi:
                sell_amount = trade_btc
                sell_value = sell_amount * row['price']
                
                cash += sell_value
                trade_btc = 0
                sold_layers.add('layer3')
                
                sells.append({
                    'date': row['date'],
                    'layer': 3,
                    'price': row['price'],
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': f'回調 {drawdown*100:.1f}%' if trigger_drawdown else 'RSI <70'
                })
    
    # 計算結果
    current_price = df.iloc[-1]['price']
    btc_value = (core_btc + trade_btc) * current_price
    total_value = btc_value + cash
    
    hodl_value = initial_btc * current_price
    
    print(f"\n{'='*70}")
    print("💰 回測結果")
    print(f"{'='*70}\n")
    
    print(f"持倉狀況：")
    print(f"  核心倉：{core_btc:.4f} BTC（永不賣）")
    print(f"  交易倉剩餘：{trade_btc:.4f} BTC")
    print(f"  總 BTC：{core_btc + trade_btc:.4f} BTC")
    print(f"  現金：${cash:,.0f}")
    
    print(f"\n當前價值（${current_price:,.0f}）：")
    print(f"  策略總價值：${total_value:,.0f}")
    print(f"  HODL 價值：${hodl_value:,.0f}")
    print(f"  差異：{(total_value - hodl_value) / hodl_value * 100:+.2f}%")
    
    print(f"\n觸發層數：{len(sold_layers)}/3")
    
    if sells:
        print(f"\n賣出記錄：")
        for sell in sells:
            print(f"  {sell['date'].date()} | 層 {sell['layer']} | ${sell['price']:>7,.0f} | "
                  f"{sell['btc']:.6f} BTC → ${sell['value']:>10,.0f}")
            print(f"    觸發原因：{sell['reason']}")
    
    # 統計摘要
    print(f"\n{'='*70}")
    print("📊 數據統計")
    print(f"{'='*70}\n")
    
    print(f"起始價格（2020-01-01）：${df.iloc[0]['price']:,.0f}")
    print(f"歷史最高價：${df['price'].max():,.0f}（{df[df['price'] == df['price'].max()].iloc[0]['date'].date()}）")
    print(f"當前價格：${current_price:,.0f}")
    print(f"總漲幅：{(current_price - df.iloc[0]['price']) / df.iloc[0]['price'] * 100:+.2f}%")
    
    return sells, total_value, cash, hodl_value

def main():
    """主函數"""
    print("="*70)
    print("📊 1.5x ATH 策略回測（2020-2025）")
    print("="*70)
    
    df = fetch_historical_data()
    sells, total_value, cash, hodl_value = backtest_1_5x_ath(df)
    
    print(f"\n{'='*70}")
    print("✅ 結論")
    print(f"{'='*70}\n")
    
    if len(sells) > 0:
        print(f"策略有效：觸發 {len(sells)} 次賣出")
        print(f"現金鎖定：${cash:,.0f}")
        print(f"vs HODL：{(total_value - hodl_value) / hodl_value * 100:+.2f}%")
    else:
        print(f"⚠️ 未觸發任何賣出")
        print(f"可能原因：閾值設置需要調整")

if __name__ == "__main__":
    main()
