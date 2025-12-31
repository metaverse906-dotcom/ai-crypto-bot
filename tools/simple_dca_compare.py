#!/usr/bin/env python3
# tools/simple_dca_compare.py
"""
簡化版 DCA 對比：直接輸出到文件
"""

import pandas as pd
import pandas_ta as ta

def compare_strategies():
    # 載入數據
    df = pd.read_csv('data/backtest/BTC_2021_2024_daily.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # 週線
    df_weekly = df.resample('W').last().dropna()
    df_weekly['rsi'] = ta.rsi(df_weekly['close'], length=14)
    
    results = []
    
    # 普通 DCA
    invested_normal = 0
    btc_normal = 0
    for idx, row in df_weekly.iterrows():
        price = row['close']
        invested_normal += 250
        btc_normal += 250 / price
    
    value_normal = btc_normal * df_weekly.iloc[-1]['close']
    roi_normal = ((value_normal / invested_normal) - 1) * 100
    
    results.append({
        'name': 'Normal DCA',
        'invested': invested_normal,
        'btc': btc_normal,
        'value': value_normal,
        'roi': roi_normal,
        'avg_cost': invested_normal / btc_normal
    })
    
    # Smart DCA (保守)
    invested_smart = 0
    btc_smart = 0
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):
            continue
        price = row['close']
        rsi = row['rsi']
        
        if rsi < 25:
            amount = 500
        elif rsi < 35:
            amount = 325
        elif rsi > 80:
            amount = 175
        elif rsi > 75:
            amount = 212
        else:
            amount = 250
        
        invested_smart += amount
        btc_smart += amount / price
    
    value_smart = btc_smart * df_weekly.iloc[-1]['close']
    roi_smart = ((value_smart / invested_smart) - 1) * 100
    
    results.append({
        'name': 'Smart DCA',
        'invested': invested_smart,
        'btc': btc_smart,
        'value': value_smart,
        'roi': roi_smart,
        'avg_cost': invested_smart / btc_smart
    })
    
    # 輸出到文件
    with open('dca_comparison_result.txt', 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("DCA Strategy Comparison (2021-2024)\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Period: {df.index[0].date()} to {df.index[-1].date()}\n")
        f.write(f"Weeks: {len(df_weekly)}\n")
        f.write(f"Price range: ${df['low'].min():.0f} - ${df['high'].max():.0f}\n\n")
        
        for r in results:
            f.write(f"【{r['name']}】\n")
            f.write(f"  Total invested: ${r['invested']:,.0f}\n")
            f.write(f"  BTC accumulated: {r['btc']:.6f}\n")
            f.write(f"  Average cost: ${r['avg_cost']:,.2f}\n")
            f.write(f"  Final value: ${r['value']:,.2f}\n")
            f.write(f"  ROI: {r['roi']:.2f}%\n\n")
        
        # 比較
        diff_btc = results[1]['btc'] - results[0]['btc']
        diff_roi = results[1]['roi'] - results[0]['roi']
        diff_cost = results[1]['avg_cost'] - results[0]['avg_cost']
        
        f.write("="*70 + "\n")
        f.write("Comparison\n")
        f.write("="*70 + "\n\n")
        f.write(f"BTC difference: {diff_btc:+.6f} ({diff_btc/results[0]['btc']*100:+.2f}%)\n")
        f.write(f"ROI difference: {diff_roi:+.2f}%\n")
        f.write(f"Average cost difference: ${diff_cost:+,.2f}\n\n")
        
        if diff_roi > 0:
            f.write(f"Result: Smart DCA wins by {diff_roi:.2f}%\n")
        else:
            f.write(f"Result: Normal DCA wins by {abs(diff_roi):.2f}%\n")
    
    print("Results saved to dca_comparison_result.txt")
    
    # 也打印到控制台
    for r in results:
        print(f"{r['name']}: {r['roi']:.2f}% | BTC: {r['btc']:.6f}")

if __name__ == "__main__":
    compare_strategies()
