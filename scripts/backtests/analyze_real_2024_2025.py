#!/usr/bin/env python3
# scripts/backtests/analyze_real_2024_2025.py
"""
分析 2024-2025 真實數據
計算技術指標並回測三層策略
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "btc_2024_2025.csv"

def calculate_indicators(df):
    """計算技術指標"""
    print("📊 計算技術指標...")
    
    # RSI
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 移動平均線
    df['ma_200'] = df['price'].rolling(window=200).mean()
    df['ma_111'] = df['price'].rolling(window=111).mean()
    df['ma_350'] = df['price'].rolling(window=350).mean()
    
    # Pi Cycle Top
    df['pi_cycle_top'] = df['ma_350'] * 2
    df['pi_cycle_signal'] = (df['ma_111'] > df['pi_cycle_top'])
    
    # MVRV 代理（價格 / 200 MA）
    df['mvrv_proxy'] = df['price'] / df['ma_200']
    
    return df

def analyze_triggers(df):
    """分析觸發點"""
    print("\n🔍 分析觸發點...")
    
    # 層 1 觸發（MVRV > 3.5）
    layer1_triggers = df[df['mvrv_proxy'] > 3.5]
    
    # 層 2 觸發（MVRV > 5.5）
    layer2_triggers = df[df['mvrv_proxy'] > 5.5]
    
    # Pi Cycle 交叉
    pi_cycle_crosses = df[df['pi_cycle_signal'] == True]
    
    print(f"\n層 1 觸發（MVRV > 3.5）：{len(layer1_triggers)} 天")
    if len(layer1_triggers) > 0:
        first_trigger = layer1_triggers.iloc[0]
        print(f"  首次觸發：{first_trigger['date'].date()}")
        print(f"  價格：${first_trigger['price']:,.0f}")
        print(f"  MVRV：{first_trigger['mvrv_proxy']:.2f}")
    
    print(f"\n層 2 觸發（MVRV > 5.5）：{len(layer2_triggers)} 天")
    if len(layer2_triggers) > 0:
        first_trigger = layer2_triggers.iloc[0]
        print(f"  首次觸發：{first_trigger['date'].date()}")
        print(f"  價格：${first_trigger['price']:,.0f}")
        print(f"  MVRV：{first_trigger['mvrv_proxy']:.2f}")
    
    print(f"\nPi Cycle 交叉：{len(pi_cycle_crosses)} 天")
    if len(pi_cycle_crosses) > 0:
        first_cross = pi_cycle_crosses.iloc[0]
        print(f"  首次交叉：{first_cross['date'].date()}")
        print(f"  價格：${first_cross['price']:,.0f}")
        print(f"  111 DMA：${first_cross['ma_111']:,.0f}")
        print(f"  350 DMA × 2：${first_cross['pi_cycle_top']:,.0f}")
    else:
        print(f"  ❌ 未觸發")
    
    return layer1_triggers, layer2_triggers, pi_cycle_crosses

def backtest_three_layer(df):
    """回測三層策略"""
    print("\n📊 回測三層策略...")
    
    initial_btc = 1.0
    core_ratio = 0.4
    
    core_btc = initial_btc * core_ratio
    trade_btc = initial_btc * (1 - core_ratio)
    cash = 0.0
    
    sells = []
    sold_layers = set()
    
    for idx, row in df.iterrows():
        if trade_btc <= 0:
            continue
        
        # 層 1
        if row['mvrv_proxy'] > 3.5 and 'layer1' not in sold_layers:
            sell_amount = initial_btc * (1 - core_ratio) * 0.02
            sell_value = sell_amount * row['price']
            
            cash += sell_value
            trade_btc -= sell_amount
            sold_layers.add('layer1')
            
            sells.append({
                'date': row['date'],
                'layer': '層 1（2%）',
                'price': row['price'],
                'btc': sell_amount,
                'value': sell_value
            })
        
        # 層 2
        if row['mvrv_proxy'] > 5.5 and 'layer2' not in sold_layers:
            remaining = initial_btc * (1 - core_ratio) * 0.98
            sell_amount = remaining * (10/98)
            sell_value = sell_amount * row['price']
            
            cash += sell_value
            trade_btc -= sell_amount
            sold_layers.add('layer2')
            
            sells.append({
                'date': row['date'],
                'layer': '層 2（10%）',
                'price': row['price'],
                'btc': sell_amount,
                'value': sell_value
            })
        
        # 層 3
        if row['pi_cycle_signal'] and 'layer3' not in sold_layers:
            sell_amount = trade_btc
            sell_value = sell_amount * row['price']
            
            cash += sell_value
            trade_btc = 0
            sold_layers.add('layer3')
            
            sells.append({
                'date': row['date'],
                'layer': '層 3（Pi Cycle）',
                'price': row['price'],
                'btc': sell_amount,
                'value': sell_value
            })
    
    # 當前價值
    current_price = df.iloc[-1]['price']
    btc_value = (core_btc + trade_btc) * current_price
    total_value = btc_value + cash
    
    print(f"\n{'='*70}")
    print("💰 回測結果")
    print(f"{'='*70}")
    
    print(f"\n持倉狀況：")
    print(f"  核心倉：{core_btc:.4f} BTC")
    print(f"  交易倉剩餘：{trade_btc:.4f} BTC")
    print(f"  總 BTC：{core_btc + trade_btc:.4f} BTC")
    print(f"  現金：${cash:,.0f}")
    
    print(f"\n當前價值（${current_price:,.0f}）：")
    print(f"  BTC 價值：${btc_value:,.0f}")
    print(f"  總價值：${total_value:,.0f}")
    
    print(f"\n觸發層數：{len(sold_layers)}/3")
    
    if sells:
        print(f"\n賣出記錄：")
        for sell in sells:
            print(f"  {sell['date'].date()} | {sell['layer']:<15} | ${sell['price']:>7,.0f} | "
                  f"{sell['btc']:.6f} BTC → ${sell['value']:>10,.0f}")
    else:
        print(f"\n⚠️ 未觸發任何賣出")
    
    # 與 HODL 對比
    hodl_value = initial_btc * current_price
    print(f"\nvs HODL：")
    print(f"  HODL 價值：${hodl_value:,.0f}")
    print(f"  三層策略：${total_value:,.0f}")
    print(f"  差異：{(total_value - hodl_value) / hodl_value * 100:+.2f}% "
          f"（${total_value - hodl_value:+,.0f}）")
    
    return sells, total_value, cash


def main():
    """主函數"""
    print("="*70)
    print("📊 2024-2025 真實數據分析")
    print("="*70)
    
    # 載入數據
    print(f"\n載入數據：{DATA_FILE}")
    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"數據範圍：{df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"數據點數：{len(df)} 天")
    
    # 計算指標
    df = calculate_indicators(df)
    
    # 分析觸發點
    layer1, layer2, pi_cycle = analyze_triggers(df)
    
    # 回測
    sells, total_value, cash = backtest_three_layer(df)
    
    # 關鍵洞察
    print(f"\n{'='*70}")
    print("💡 關鍵洞察")
    print(f"{'='*70}")
    
    max_price = df['price'].max()
    max_date = df[df['price'] == max_price].iloc[0]['date']
    current_price = df.iloc[-1]['price']
    
    print(f"\n歷史最高價：${max_price:,.0f}（{max_date.date()}）")
    print(f"當前價格：${current_price:,.0f}")
    print(f"回調：{(current_price - max_price) / max_price * 100:+.2f}%")
    
    if len(sells) > 0:
        print(f"\n三層策略表現：")
        print(f"  ✅ 觸發 {len(sells)} 個賣出層")
        print(f"  現金鎖定：${cash:,.0f}")
    else:
        print(f"\n⚠️ 三層策略未觸發任何賣出")
        print(f"  可能原因：MVRV 未達到觸發閾值")


if __name__ == "__main__":
    main()
