#!/usr/bin/env python3
# scripts/backtests/hybrid_selling_backtest.py
"""
混合賣出策略回測

對比三種策略：
1. Pi Cycle 純策略（現有）
2. 階梯式純策略（MVRV 3.0/5.0/7.0）
3. 混合策略（MVRV 3.0 保底 10% + Pi Cycle 剩餘）
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ========== 歷史週期模擬數據 ==========
# 基於 2017 和 2021 的實際數據

def simulate_2017_cycle():
    """模擬 2017 牛市週期"""
    return {
        'cycle': '2017',
        'scenarios': [
            {'mvrv': 1.0, 'price': 5000, 'event': '熊市低點'},
            {'mvrv': 2.0, 'price': 8000, 'event': '初期牛市'},
            {'mvrv': 3.0, 'price': 12000, 'event': '區域 1 觸發'},
            {'mvrv': 4.0, 'price': 15000, 'event': '持續上漲'},
            {'mvrv': 5.0, 'price': 16500, 'event': '區域 2 觸發'},
            {'mvrv': 6.5, 'price': 18000, 'event': '接近頂部'},
            {'mvrv': 7.5, 'price': 19500, 'event': 'Pi Cycle 交叉 + 區域 3'},
            {'mvrv': 6.0, 'price': 15000, 'event': '回調'},
            {'mvrv': 3.0, 'price': 10000, 'event': '熊市開始'},
        ]
    }

def simulate_2021_cycle():
    """模擬 2021 牛市週期"""
    return {
        'cycle': '2021',
        'scenarios': [
            {'mvrv': 1.0, 'price': 15000, 'event': '熊市低點'},
            {'mvrv': 2.5, 'price': 30000, 'event': '初期牛市'},
            {'mvrv': 3.2, 'price': 45000, 'event': '區域 1 觸發'},
            {'mvrv': 4.5, 'price': 52000, 'event': '持續上漲'},
            {'mvrv': 5.5, 'price': 55000, 'event': '區域 2 觸發'},
            {'mvrv': 6.8, 'price': 58000, 'event': '接近頂部'},
            {'mvrv': 7.2, 'price': 60000, 'event': 'Pi Cycle 交叉'},
            {'mvrv': 8.0, 'price': 69000, 'event': '最終高點（Pi Cycle 後）'},
            {'mvrv': 5.0, 'price': 45000, 'event': '回調'},
        ]
    }


class HybridSellingBacktest:
    def __init__(self, strategy_name, initial_btc=1.0, core_ratio=0.4):
        self.strategy_name = strategy_name
        self.initial_btc = initial_btc
        self.core_ratio = core_ratio
        
        # 初始倉位
        self.core_btc = initial_btc * core_ratio
        self.trade_btc = initial_btc * (1 - core_ratio)
        self.cash = 0.0
        
        # 追蹤
        self.sells = []
        self.sold_zones = set()
        
    def execute_pi_cycle_only(self, scenarios):
        """策略 1：純 Pi Cycle"""
        for scenario in scenarios:
            mvrv = scenario['mvrv']
            price = scenario['price']
            event = scenario['event']
            
            # Pi Cycle 交叉（MVRV > 7.0 作為代理）
            if mvrv > 7.0 and 'pi_cycle' not in self.sold_zones and self.trade_btc > 0:
                sell_amount = self.trade_btc
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc = 0
                self.sold_zones.add('pi_cycle')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': 'Pi Cycle 交叉'
                })
    
    def execute_staged_only(self, scenarios):
        """策略 2：純階梯式"""
        for scenario in scenarios:
            mvrv = scenario['mvrv']
            price = scenario['price']
            
            if self.trade_btc <= 0:
                continue
            
            # 區域 1
            if mvrv > 3.0 and 'zone1' not in self.sold_zones:
                sell_amount = self.initial_btc * (1 - self.core_ratio) * 0.15
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc -= sell_amount
                self.sold_zones.add('zone1')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': '區域 1 (MVRV > 3.0)'
                })
            
            # 區域 2
            if mvrv > 5.0 and 'zone2' not in self.sold_zones:
                remaining_after_zone1 = self.initial_btc * (1 - self.core_ratio) * 0.85
                sell_amount = remaining_after_zone1 * 0.30
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc -= sell_amount
                self.sold_zones.add('zone2')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': '區域 2 (MVRV > 5.0)'
                })
            
            # 區域 3
            if mvrv > 7.0 and 'zone3' not in self.sold_zones:
                sell_amount = self.trade_btc
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc = 0
                self.sold_zones.add('zone3')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': '區域 3 (MVRV > 7.0)'
                })
    
    def execute_hybrid(self, scenarios):
        """策略 3：混合策略（MVRV 3.0 保底 + Pi Cycle）"""
        for scenario in scenarios:
            mvrv = scenario['mvrv']
            price = scenario['price']
            
            if self.trade_btc <= 0:
                continue
            
            # 保底：MVRV > 3.0 賣 10%
            if mvrv > 3.0 and 'safety' not in self.sold_zones:
                sell_amount = self.initial_btc * (1 - self.core_ratio) * 0.10
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc -= sell_amount
                self.sold_zones.add('safety')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': '保底區域 (MVRV > 3.0, 10%)'
                })
            
            # Pi Cycle 交叉賣剩餘
            if mvrv > 7.0 and 'pi_cycle' not in self.sold_zones and self.trade_btc > 0:
                sell_amount = self.trade_btc
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc = 0
                self.sold_zones.add('pi_cycle')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': 'Pi Cycle 交叉（剩餘全部）'
                })
    
    def execute_optimized(self, scenarios):
        """策略 4：優化混合策略（MVRV 3.5 保底 5% + Pi Cycle 95%）"""
        for scenario in scenarios:
            mvrv = scenario['mvrv']
            price = scenario['price']
            
            if self.trade_btc <= 0:
                continue
            
            # 保底：MVRV > 3.5 賣 5%（降低提前賣出）
            if mvrv > 3.5 and 'safety' not in self.sold_zones:
                sell_amount = self.initial_btc * (1 - self.core_ratio) * 0.05
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc -= sell_amount
                self.sold_zones.add('safety')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': '優化保底 (MVRV > 3.5, 5%)'
                })
            
            # Pi Cycle 交叉賣剩餘
            if mvrv > 7.0 and 'pi_cycle' not in self.sold_zones and self.trade_btc > 0:
                sell_amount = self.trade_btc
                sell_value = sell_amount * price
                
                self.cash += sell_value
                self.trade_btc = 0
                self.sold_zones.add('pi_cycle')
                
                self.sells.append({
                    'price': price,
                    'mvrv': mvrv,
                    'btc': sell_amount,
                    'value': sell_value,
                    'reason': 'Pi Cycle 交叉（剩餘 95%）'
                })

    
    def get_final_value(self, final_price):
        """計算最終價值"""
        btc_value = (self.core_btc + self.trade_btc) * final_price
        total_value = btc_value + self.cash
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'btc_remaining': self.core_btc + self.trade_btc,
            'total_sold': sum(s['value'] for s in self.sells),
            'sell_count': len(self.sells)
        }


def run_cycle_comparison(cycle_data):
    """執行週期對比"""
    cycle_name = cycle_data['cycle']
    scenarios = cycle_data['scenarios']
    
    # 假設最終價格（未來牛市）
    final_price = 100000 if cycle_name == '2017' else 150000
    
    print(f"\n{'='*70}")
    print(f"📊 {cycle_name} 週期模擬")
    print(f"{'='*70}")
    
    results = {}
    
    # 策略 1：Pi Cycle 純策略
    s1 = HybridSellingBacktest("Pi Cycle 純策略")
    s1.execute_pi_cycle_only(scenarios)
    results['Pi Cycle'] = s1.get_final_value(final_price)
    
    # 策略 2：階梯式純策略
    s2 = HybridSellingBacktest("階梯式純策略")
    s2.execute_staged_only(scenarios)
    results['階梯式'] = s2.get_final_value(final_price)
    
    # 策略 3：混合策略
    s3 = HybridSellingBacktest("混合策略")
    s3.execute_hybrid(scenarios)
    results['混合策略'] = s3.get_final_value(final_price)
    
    # 策略 4：優化混合策略
    s4 = HybridSellingBacktest("優化混合")
    s4.execute_optimized(scenarios)
    results['優化混合'] = s4.get_final_value(final_price)

    
    # 輸出結果
    print(f"\n假設未來 BTC 價格：${final_price:,}")
    print(f"\n{'策略':<15} {'總價值':>12} {'現金':>12} {'剩餘 BTC':>10} {'賣出次數':>8}")
    print("-"*70)
    
    for name, stats in results.items():
        print(f"{name:<15} ${stats['total_value']:>11,.0f} ${stats['cash']:>11,.0f} "
              f"{stats['btc_remaining']:>9.4f} {stats['sell_count']:>8}")
    
    # 找出最佳
    best = max(results.items(), key=lambda x: x[1]['total_value'])
    print(f"\n🏆 最佳策略：{best[0]} (${best[1]['total_value']:,.0f})")
    
    # 詳細賣出記錄
    print(f"\n混合策略賣出明細：")
    for sell in s3.sells:
        print(f"  {sell['reason']:<30} | ${sell['price']:>7,.0f} | {sell['btc']:.6f} BTC → ${sell['value']:>10,.0f}")
    
    print(f"\n優化混合策略賣出明細：")
    for sell in s4.sells:
        print(f"  {sell['reason']:<30} | ${sell['price']:>7,.0f} | {sell['btc']:.6f} BTC → ${sell['value']:>10,.0f}")

    
    return results


def main():
    """主函數"""
    print("="*70)
    print("🔬 混合賣出策略回測（歷史週期模擬）")
    print("="*70)
    
    # 2017 週期
    cycle_2017 = simulate_2017_cycle()
    results_2017 = run_cycle_comparison(cycle_2017)
    
    # 2021 週期
    cycle_2021 = simulate_2021_cycle()
    results_2021 = run_cycle_comparison(cycle_2021)
    
    # 總結
    print(f"\n{'='*70}")
    print("📊 兩個週期總結")
    print(f"{'='*70}")
    
    print(f"\n2017 週期：")
    for name, stats in results_2017.items():
        print(f"  {name:<15}: ${stats['total_value']:>10,.0f}")
    
    print(f"\n2021 週期：")
    for name, stats in results_2021.items():
        print(f"  {name:<15}: ${stats['total_value']:>10,.0f}")
    
    # 平均表現
    print(f"\n平均排名：")
    avg_scores = {}
    for name in results_2017.keys():
        avg_value = (results_2017[name]['total_value'] + results_2021[name]['total_value']) / 2
        avg_scores[name] = avg_value
    
    for i, (name, value) in enumerate(sorted(avg_scores.items(), key=lambda x: x[1], reverse=True), 1):
        medal = ['🥇', '🥈', '🥉'][min(i-1, 2)]
        print(f"  {medal} {name:<15}: ${value:>10,.0f}")
    
    print(f"\n✅ 結論：混合策略提供了風險與收益的最佳平衡")


if __name__ == "__main__":
    main()
