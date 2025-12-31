#!/usr/bin/env python3
# tools/fixed_smart_dca.py
"""
修正版 Smart DCA 完整測試
"""

import pandas as pd
import pandas_ta as ta

def test_all_strategies():
    # 載入數據
    df = pd.read_csv('data/backtest/BTC_2021_2024_daily.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # 週線
    df_weekly = df.resample('W').last().dropna()
    df_weekly['rsi'] = ta.rsi(df_weekly['close'], length=14)
    df_weekly['ma200'] = ta.sma(df_weekly['close'], length=200)
    
    print("="*70)
    print("Smart DCA 修正版測試")
    print("="*70)
    print(f"期間: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"週數: {len(df_weekly)}\n")
    
    # === 策略1：普通DCA ===
    invested1 = 0
    btc1 = 0
    for idx, row in df_weekly.iterrows():
        invested1 += 250
        btc1 += 250 / row['close']
    
    final_price = df_weekly.iloc[-1]['close']
    value1 = btc1 * final_price
    roi1 = ((value1 / invested1) - 1) * 100
    
    print(f"【普通 DCA】")
    print(f"  投入: ${invested1:,.0f}")
    print(f"  BTC: {btc1:.6f}")
    print(f"  總資產: ${value1:,.2f}")
    print(f"  報酬率: {roi1:.2f}%\n")
    
    # === 策略2：Smart DCA (只買) ===
    invested2 = 0
    btc2 = 0
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):
            continue
        rsi = row['rsi']
        
        if rsi < 25: amount = 500
        elif rsi < 35: amount = 325
        elif rsi > 80: amount = 175
        elif rsi > 75: amount = 212
        else: amount = 250
        
        invested2 += amount
        btc2 += amount / row['close']
    
    value2 = btc2 * final_price
    roi2 = ((value2 / invested2) - 1) * 100
    
    print(f"【Smart DCA (只買)】")
    print(f"  投入: ${invested2:,.0f}")
    print(f"  BTC: {btc2:.6f}")
    print(f"  總資產: ${value2:,.2f}")
    print(f"  報酬率: {roi2:.2f}%\n")
    
    # === 策略3：Smart DCA (買低賣高) ===
    weekly_cash = 250
    total_cash = 0  # 總投入現金
    btc3 = 0
    usdt_reserve = 0
    sell_count = 0
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):  # 只檢查RSI（14週後就有）
            continue
        
        price = row['close']
        rsi = row['rsi']
        
        # 每週投入現金
        total_cash += weekly_cash
        
        # 賣出邏輯（需要MA200）
        if btc3 > 0 and not pd.isna(row['ma200']):
            ma200 = row['ma200']
            if rsi > 75 and price > ma200 * 1.3:
                sell_btc = btc3 * 0.3
                usdt_reserve += sell_btc * price
                btc3 -= sell_btc
                sell_count += 1
        
        # 決定買入金額
        buy_amount = weekly_cash
        
        if rsi < 25: buy_amount *= 2
        elif rsi < 35: buy_amount *= 1.5
        elif rsi > 75: buy_amount *= 0.7
        
        # 動用儲備
        if usdt_reserve > 0 and rsi < 40:
            extra = min(usdt_reserve * 0.5, weekly_cash)
            buy_amount += extra
            usdt_reserve -= extra
        
        # 買入
        btc3 += buy_amount / price
    
    btc_value3 = btc3 * final_price
    value3 = btc_value3 + usdt_reserve
    roi3 = ((value3 / total_cash) - 1) * 100
    
    print(f"【Smart DCA (買低賣高)】")
    print(f"  投入: ${total_cash:,.0f}")
    print(f"  BTC: {btc3:.6f}")
    print(f"  USDT儲備: ${usdt_reserve:,.2f}")
    print(f"  BTC價值: ${btc_value3:,.2f}")
    print(f"  總資產: ${value3:,.2f}")
    print(f"  報酬率: {roi3:.2f}%")
    print(f"  賣出次數: {sell_count}\n")
    
    # 比較
    print("="*70)
    print("績效比較")
    print("="*70)
    print(f"Smart (只買) vs 普通: {roi2 - roi1:+.2f}%")
    print(f"Smart (買低賣高) vs 普通: {roi3 - roi1:+.2f}%")
    print(f"買低賣高 vs 只買: {roi3 - roi2:+.2f}%")

if __name__ == "__main__":
    test_all_strategies()
