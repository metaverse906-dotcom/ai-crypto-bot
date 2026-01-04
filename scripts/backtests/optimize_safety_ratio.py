#!/usr/bin/env python3
# scripts/backtests/optimize_safety_ratio.py
"""
優化保底比例

測試不同保底比例（1-10%）找出最佳平衡點
目標：最大化期望值（考慮 Pi Cycle 失效風險）
"""

import pandas as pd

def calculate_strategy_value(safety_ratio, scenarios, final_price, pi_fail_prob=0.3):
    """
    計算策略價值
    
    Args:
        safety_ratio: 保底比例（0.01-0.10）
        scenarios: 價格情境
        final_price: 未來價格
        pi_fail_prob: Pi Cycle 失效機率
    """
    initial_btc = 1.0
    core_ratio = 0.4
    
    core_btc = initial_btc * core_ratio
    trade_btc = initial_btc * (1 - core_ratio)
    
    cash = 0.0
    safety_sold = False
    pi_sold = False
    
    # 執行策略
    for scenario in scenarios:
        mvrv = scenario['mvrv']
        price = scenario['price']
        
        # 保底區域
        if mvrv > 3.5 and not safety_sold and trade_btc > 0:
            sell_amount = initial_btc * (1 - core_ratio) * safety_ratio
            cash += sell_amount * price
            trade_btc -= sell_amount
            safety_sold = True
        
        # Pi Cycle
        if mvrv > 7.0 and not pi_sold and trade_btc > 0:
            cash += trade_btc * price
            trade_btc = 0
            pi_sold = True
    
    # 計算兩種情境的價值
    # 情境 A：Pi Cycle 正常運作
    normal_value = (core_btc + trade_btc) * final_price + cash
    
    # 情境 B：Pi Cycle 失效（熊市價格）
    bear_price = final_price * 0.2  # 假設熊市跌 80%
    fail_value = (core_btc + initial_btc * (1 - core_ratio) * (1 - safety_ratio)) * bear_price + cash
    
    # 期望值
    expected_value = normal_value * (1 - pi_fail_prob) + fail_value * pi_fail_prob
    
    return {
        'safety_ratio': safety_ratio,
        'normal_value': normal_value,
        'fail_value': fail_value,
        'expected_value': expected_value,
        'cash_secured': cash
    }


def simulate_2017():
    """2017 週期"""
    return {
        'scenarios': [
            {'mvrv': 1.0, 'price': 5000},
            {'mvrv': 3.0, 'price': 12000},
            {'mvrv': 3.7, 'price': 13500},  # 保底觸發
            {'mvrv': 5.0, 'price': 16500},
            {'mvrv': 7.5, 'price': 19500},  # Pi Cycle
        ],
        'final_price': 100000
    }


def simulate_2021():
    """2021 週期"""
    return {
        'scenarios': [
            {'mvrv': 1.0, 'price': 15000},
            {'mvrv': 3.2, 'price': 45000},
            {'mvrv': 3.8, 'price': 47000},  # 保底觸發
            {'mvrv': 5.5, 'price': 55000},
            {'mvrv': 7.2, 'price': 60000},  # Pi Cycle
        ],
        'final_price': 150000
    }


def optimize_safety_ratio():
    """優化保底比例"""
    print("="*70)
    print("🔬 保底比例優化分析")
    print("="*70)
    
    # 測試不同比例
    test_ratios = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15]
    
    cycle_2017 = simulate_2017()
    cycle_2021 = simulate_2021()
    
    results_2017 = []
    results_2021 = []
    
    # Pi Cycle 純策略基準
    baseline_2017 = calculate_strategy_value(0.0, cycle_2017['scenarios'], cycle_2017['final_price'])
    baseline_2021 = calculate_strategy_value(0.0, cycle_2021['scenarios'], cycle_2021['final_price'])
    
    print(f"\n📊 基準（Pi Cycle 純策略）：")
    print(f"  2017：正常 ${baseline_2017['normal_value']:,.0f} | 失效 ${baseline_2017['fail_value']:,.0f} | 期望 ${baseline_2017['expected_value']:,.0f}")
    print(f"  2021：正常 ${baseline_2021['normal_value']:,.0f} | 失效 ${baseline_2021['fail_value']:,.0f} | 期望 ${baseline_2021['expected_value']:,.0f}")
    
    print(f"\n{'比例':<6} {'2017 正常':<12} {'2017 期望':<12} {'2021 正常':<12} {'2021 期望':<12} {'平均期望':<12}")
    print("-"*70)
    
    for ratio in test_ratios:
        r2017 = calculate_strategy_value(ratio, cycle_2017['scenarios'], cycle_2017['final_price'])
        r2021 = calculate_strategy_value(ratio, cycle_2021['scenarios'], cycle_2021['final_price'])
        
        results_2017.append(r2017)
        results_2021.append(r2021)
        
        avg_expected = (r2017['expected_value'] + r2021['expected_value']) / 2
        
        print(f"{ratio*100:>5.0f}% ${r2017['normal_value']:>10,.0f} ${r2017['expected_value']:>10,.0f} "
              f"${r2021['normal_value']:>10,.0f} ${r2021['expected_value']:>10,.0f} ${avg_expected:>10,.0f}")
    
    # 找出最佳比例（基於平均期望值）
    avg_expected_values = [(r2017['expected_value'] + r2021['expected_value']) / 2 
                           for r2017, r2021 in zip(results_2017, results_2021)]
    
    best_idx = avg_expected_values.index(max(avg_expected_values))
    best_ratio = test_ratios[best_idx]
    best_expected = avg_expected_values[best_idx]
    
    print(f"\n🏆 最佳保底比例：{best_ratio*100:.0f}%")
    print(f"   平均期望值：${best_expected:,.0f}")
    
    # 詳細分析最佳比例
    print(f"\n📊 最佳比例（{best_ratio*100:.0f}%）詳細分析：")
    
    best_2017 = results_2017[best_idx]
    best_2021 = results_2021[best_idx]
    
    print(f"\n2017 週期：")
    print(f"  正常情境（70%）：${best_2017['normal_value']:,.0f}")
    print(f"  失效情境（30%）：${best_2017['fail_value']:,.0f}")
    print(f"  期望值：${best_2017['expected_value']:,.0f}")
    print(f"  vs Pi Cycle：{(best_2017['normal_value'] - baseline_2017['normal_value']) / baseline_2017['normal_value'] * 100:+.2f}%")
    
    print(f"\n2021 週期：")
    print(f"  正常情境（70%）：${best_2021['normal_value']:,.0f}")
    print(f"  失效情境（30%）：${best_2021['fail_value']:,.0f}")
    print(f"  期望值：${best_2021['expected_value']:,.0f}")
    print(f"  vs Pi Cycle：{(best_2021['normal_value'] - baseline_2021['normal_value']) / baseline_2021['normal_value'] * 100:+.2f}%")
    
    # 對比分析
    print(f"\n💡 關鍵洞察：")
    
    # 找出正常情境最佳（損失最少）
    normal_loss_2017 = [(r['normal_value'] - baseline_2017['normal_value']) / baseline_2017['normal_value'] * 100 
                        for r in results_2017]
    best_normal_idx = normal_loss_2017.index(max(normal_loss_2017))
    
    print(f"\n  最小損失（正常情境）：{test_ratios[best_normal_idx]*100:.0f}%")
    print(f"  損失：{normal_loss_2017[best_normal_idx]:+.2f}%")
    
    print(f"\n  最高期望值：{best_ratio*100:.0f}%")
    print(f"  期望值：${best_expected:,.0f}")
    
    if best_idx != best_normal_idx:
        print(f"\n  ⚠️ 注意：最小損失比例 ≠ 最高期望值比例")
        print(f"  建議：如果你相信 Pi Cycle 可靠性高（>80%），選 {test_ratios[best_normal_idx]*100:.0f}%")
        print(f"       如果你擔心 Pi Cycle 失效風險（20-30%），選 {best_ratio*100:.0f}%")
    
    return test_ratios[best_idx]


if __name__ == "__main__":
    best = optimize_safety_ratio()
    print(f"\n✅ 最終建議：保底比例 {best*100:.0f}%")
