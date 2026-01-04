#!/usr/bin/env python3
# scripts/backtests/optimize_mvrv_thresholds.py
"""
優化 MVRV 閾值

基於 2024-2025 真實數據
測試不同閾值組合，找出最佳配置
"""

import pandas as pd
import numpy as np
from pathlib import Path
from itertools import product

DATA_FILE = Path(__file__).parent / "data" / "btc_2024_2025.csv"

def calculate_mvrv(df):
    """計算 MVRV 代理"""
    df['ma_200'] = df['price'].rolling(window=200).mean()
    df['mvrv'] = df['price'] / df['ma_200']
    return df

def backtest_strategy(df, threshold1, ratio1, threshold2, ratio2, threshold3, ratio3):
    """
    回測策略
    
    Args:
        threshold1, ratio1: 第一層閾值和賣出比例
        threshold2, ratio2: 第二層閾值和賣出比例
        threshold3, ratio3: 第三層閾值和賣出比例
    """
    initial_btc = 1.0
    core_ratio = 0.4
    
    core_btc = initial_btc * core_ratio
    trade_btc = initial_btc * (1 - core_ratio)
    cash = 0.0
    
    sold_layers = set()
    sells = []
    
    for idx, row in df.iterrows():
        if pd.isna(row['mvrv']) or trade_btc <= 0:
            continue
        
        # 層 1
        if row['mvrv'] >= threshold1 and 'layer1' not in sold_layers:
            sell_amount = initial_btc * (1 - core_ratio) * ratio1
            cash += sell_amount * row['price']
            trade_btc -= sell_amount
            sold_layers.add('layer1')
            sells.append({
                'date': row['date'],
                'price': row['price'],
                'layer': 1
            })
        
        # 層 2
        if row['mvrv'] >= threshold2 and 'layer2' not in sold_layers:
            remaining_ratio = 1 - ratio1 if 'layer1' in sold_layers else 1.0
            sell_amount = initial_btc * (1 - core_ratio) * remaining_ratio * (ratio2 / remaining_ratio)
            cash += sell_amount * row['price']
            trade_btc -= sell_amount
            sold_layers.add('layer2')
            sells.append({
                'date': row['date'],
                'price': row['price'],
                'layer': 2
            })
        
        # 層 3
        if row['mvrv'] >= threshold3 and 'layer3' not in sold_layers:
            sell_amount = trade_btc
            cash += sell_amount * row['price']
            trade_btc = 0
            sold_layers.add('layer3')
            sells.append({
                'date': row['date'],
                'price': row['price'],
                'layer': 3
            })
    
    # 計算最終價值
    current_price = df.iloc[-1]['price']
    btc_value = (core_btc + trade_btc) * current_price
    total_value = btc_value + cash
    
    # 計算回撤（從最高點）
    max_price = df['price'].max()
    drawdown_from_peak = (current_price - max_price) / max_price
    
    # 如果在高點賣出的價值
    peak_cash_potential = 0
    if sells:
        for sell in sells:
            if sell['price'] >= max_price * 0.95:  # 接近頂部
                peak_cash_potential += 1
    
    return {
        'total_value': total_value,
        'cash': cash,
        'btc_remaining': core_btc + trade_btc,
        'layers_triggered': len(sold_layers),
        'sells': sells,
        'cash_ratio': cash / total_value if total_value > 0 else 0
    }


def optimize():
    """優化閾值"""
    print("="*70)
    print("🔬 MVRV 閾值優化分析（基於 2024-2025 真實數據）")
    print("="*70)
    
    # 載入數據
    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df = calculate_mvrv(df)
    
    # 統計 MVRV 範圍
    mvrv_valid = df[df['mvrv'].notna()]['mvrv']
    print(f"\n📊 MVRV 統計（2024-2025）：")
    print(f"  最小值：{mvrv_valid.min():.2f}")
    print(f"  最大值：{mvrv_valid.max():.2f}")
    print(f"  平均值：{mvrv_valid.mean():.2f}")
    print(f"  中位數：{mvrv_valid.median():.2f}")
    
    # 找出頂部區域的 MVRV
    top_10_pct = df.nlargest(int(len(df) * 0.1), 'price')
    print(f"\n  頂部 10% 價格區間的 MVRV：")
    print(f"    平均：{top_10_pct['mvrv'].mean():.2f}")
    print(f"    最大：{top_10_pct['mvrv'].max():.2f}")
    
    # 測試配置
    test_configs = [
        # (layer1_threshold, layer1_ratio, layer2_threshold, layer2_ratio, layer3_threshold, layer3_ratio)
        (1.8, 0.05, 2.2, 0.15, 2.6, 0.80),  # 極保守
        (2.0, 0.05, 2.5, 0.15, 3.0, 0.80),  # 保守
        (2.2, 0.05, 2.7, 0.15, 3.2, 0.80),  # 中等
        (2.5, 0.05, 3.0, 0.15, 3.5, 0.80),  # 原配置降低
        (1.5, 0.10, 2.0, 0.20, 2.5, 0.70),  # 激進早賣
        (2.0, 0.02, 2.3, 0.10, 2.8, 0.88),  # 小保底
        (1.8, 0.03, 2.3, 0.12, 2.8, 0.85),  # 平衡
    ]
    
    print(f"\n{'='*70}")
    print("測試 {len(test_configs)} 種配置...")
    print(f"{'='*70}\n")
    
    results = []
    
    for idx, config in enumerate(test_configs, 1):
        t1, r1, t2, r2, t3, r3 = config
        result = backtest_strategy(df, t1, r1, t2, r2, t3, r3)
        
        results.append({
            'config': f"閾值 {t1:.1f}/{t2:.1f}/{t3:.1f}, 比例 {r1*100:.0f}%/{r2*100:.0f}%/{r3*100:.0f}%",
            't1': t1, 't2': t2, 't3': t3,
            'r1': r1, 'r2': r2, 'r3': r3,
            **result
        })
        
        print(f"{idx}. 閾值 {t1:.1f}/{t2:.1f}/{t3:.1f} | 比例 {r1*100:.0f}%/{r2*100:.0f}%/{r3*100:.0f}%")
        print(f"   總價值: ${result['total_value']:,.0f} | 現金: ${result['cash']:,.0f} "
              f"| 觸發: {result['layers_triggered']}/3")
    
    # 排序（按總價值）
    results_sorted = sorted(results, key=lambda x: x['total_value'], reverse=True)
    
    print(f"\n{'='*70}")
    print("📊 Top 3 配置（按總價值）")
    print(f"{'='*70}\n")
    
    for i, r in enumerate(results_sorted[:3], 1):
        medal = ['🥇', '🥈', '🥉'][i-1]
        print(f"{medal} {r['config']}")
        print(f"   總價值: ${r['total_value']:,.0f}")
        print(f"   現金: ${r['cash']:,.0f} ({r['cash_ratio']*100:.1f}%)")
        print(f"   剩餘 BTC: {r['btc_remaining']:.4f}")
        print(f"   觸發層數: {r['layers_triggered']}/3")
        
        if r['sells']:
            print(f"   賣出記錄:")
            for sell in r['sells']:
                print(f"     {sell['date'].date()} | 層 {sell['layer']} | ${sell['price']:,.0f}")
        print()
    
    # 找出現金最多的
    best_cash = max(results, key=lambda x: x['cash'])
    print(f"💰 現金最多配置：")
    print(f"   {best_cash['config']}")
    print(f"   現金: ${best_cash['cash']:,.0f}")
    print(f"   總價值: ${best_cash['total_value']:,.0f}")
    
    # 對比 HODL
    current_price = df.iloc[-1]['price']
    hodl_value = 1.0 * current_price
    
    print(f"\n📊 vs HODL (${hodl_value:,.0f}):")
    print(f"   最佳策略: ${results_sorted[0]['total_value']:,.0f} "
          f"({(results_sorted[0]['total_value'] - hodl_value) / hodl_value * 100:+.2f}%)")
    
    # 推薦
    print(f"\n{'='*70}")
    print("✅ 最終推薦")
    print(f"{'='*70}\n")
    
    best = results_sorted[0]
    print(f"配置：")
    print(f"  層 1：MVRV > {best['t1']:.1f} → 賣 {best['r1']*100:.0f}%")
    print(f"  層 2：MVRV > {best['t2']:.1f} → 賣 {best['r2']*100:.0f}%")
    print(f"  層 3：MVRV > {best['t3']:.1f} → 賣 {best['r3']*100:.0f}%")
    
    print(f"\n預期結果（基於 2024-2025 數據）：")
    print(f"  總價值：${best['total_value']:,.0f}")
    print(f"  現金：${best['cash']:,.0f}")
    print(f"  觸發次數：{best['layers_triggered']}")


if __name__ == "__main__":
    optimize()
