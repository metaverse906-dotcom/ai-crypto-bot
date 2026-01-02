#!/usr/bin/env python3
"""
加權比例優化測試

測試不同的 MVRV/RSI/F&G 權重組合，找出最佳配置
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import ccxt
from core.position_manager import PositionManager
import logging
from itertools import product

logging.basicConfig(level=logging.WARNING)


def download_data():
    """下載數據"""
    print("📥 下載數據...")
    exchange = ccxt.binance()
    
    ohlcv = exchange.fetch_ohlcv(
        'BTC/USDT',
        timeframe='1w',
        since=int(datetime(2020, 1, 1).timestamp() * 1000),
        limit=1000
    )
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    import pandas_ta as ta
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ma_200w'] = df['close'].rolling(window=200, min_periods=50).mean()
    
    # MVRV 代理
    df['price_ratio'] = df['close'] / df['ma_200w']
    def ratio_to_mvrv(ratio):
        if pd.isna(ratio):
            return 1.0
        elif ratio < 1.0:
            return max(0.0, ratio * 1.0)
        elif ratio < 1.5:
            return 1.0 + (ratio - 1.0) * 3.0
        elif ratio < 2.0:
            return 2.5 + (ratio - 1.5) * 3.0
        elif ratio < 3.0:
            return 4.0 + (ratio - 2.0) * 2.5
        else:
            return min(10.0, 6.5 + (ratio - 3.0) * 1.5)
    
    df['mvrv'] = df['price_ratio'].apply(ratio_to_mvrv)
    
    # F&G 代理
    df['momentum'] = df['close'].pct_change(4)
    df['fg_proxy'] = 50 + df['momentum'] * 100
    df['fg_proxy'] = df['fg_proxy'].clip(0, 100)
    
    print(f"✅ 完成：{len(df)} 週")
    return df


class WeightedStrategy:
    """加權策略（可調整權重）"""
    
    def __init__(self, mvrv_weight, rsi_weight, fg_weight, core_ratio=0.4):
        self.mvrv_w = mvrv_weight
        self.rsi_w = rsi_weight
        self.fg_w = fg_weight
        self.core_ratio = core_ratio
        self.base_weekly = 250
        self.pm = PositionManager(core_ratio=core_ratio, data_file=None)
        self.cash = 0
        
    def calculate_score(self, mvrv, rsi, fg):
        """計算綜合分數"""
        # MVRV 映射
        if mvrv < 0.1:
            mvrv_score = 0
        elif mvrv < 1.0:
            mvrv_score = 10
        elif mvrv < 3.0:
            mvrv_score = 30
        elif mvrv < 5.0:
            mvrv_score = 50
        elif mvrv < 6.0:
            mvrv_score = 65
        elif mvrv < 7.0:
            mvrv_score = 80
        elif mvrv < 9.0:
            mvrv_score = 90
        else:
            mvrv_score = 100
        
        rsi_score = rsi if not pd.isna(rsi) else 50
        fg_score = fg if not pd.isna(fg) else 50
        
        # 加權
        composite = (mvrv_score * self.mvrv_w) + (rsi_score * self.rsi_w) + (fg_score * self.fg_w)
        return composite
    
    def get_buy_multiplier(self, score):
        if score < 15:
            return 3.5
        elif score < 25:
            return 2.0
        elif score < 35:
            return 1.5
        elif score < 50:
            return 1.0
        elif score < 60:
            return 0.5
        else:
            return 0.0
    
    def get_sell_pct(self, score):
        if score < 70:
            return 0.0
        elif score < 80:
            return 0.10
        elif score < 90:
            return 0.30
        elif score < 95:
            return 0.50
        else:
            return 1.0
    
    def run(self, df):
        for idx, row in df.iterrows():
            if pd.notna(row['mvrv']) and pd.notna(row['rsi']):
                score = self.calculate_score(row['mvrv'], row['rsi'], row['fg_proxy'])
                
                # 買入
                multiplier = self.get_buy_multiplier(score)
                if multiplier > 0:
                    buy_usd = self.base_weekly * multiplier
                    buy_btc = buy_usd / row['close']
                    self.pm.add_buy(buy_btc, row['close'], "")
                    self.cash -= buy_usd
                
                # 賣出
                sell_pct = self.get_sell_pct(score)
                if sell_pct > 0:
                    stats = self.pm.get_stats()
                    if stats['trade_btc'] > 0:
                        sell_btc = stats['trade_btc'] * sell_pct
                        try:
                            result = self.pm.execute_sell_hifo(sell_btc, row['close'])
                            self.cash += result['total_revenue']
                        except:
                            pass
        
        stats = self.pm.get_stats()
        return stats['total_btc'], stats['avg_cost']


def main():
    print("\n" + "="*80)
    print(" 🔬 加權比例優化測試")
    print("="*80)
    
    df = download_data()
    
    # HODL 基準
    total_btc_hodl = sum(250 / row['close'] for idx, row in df.iterrows() if pd.notna(row['close']))
    
    print(f"\nHODL 基準：{total_btc_hodl:.6f} BTC\n")
    
    # 測試不同權重組合
    print("🧪 測試權重組合中...\n")
    
    weight_configs = [
        # (MVRV, RSI, F&G, 名稱)
        (1.0, 0.0, 0.0, "純MVRV"),
        (0.9, 0.1, 0.0, "MVRV 90% + RSI 10%"),
        (0.8, 0.2, 0.0, "MVRV 80% + RSI 20%"),
        (0.7, 0.3, 0.0, "MVRV 70% + RSI 30%"),
        (0.6, 0.4, 0.0, "MVRV 60% + RSI 40%"),
        (0.5, 0.5, 0.0, "MVRV 50% + RSI 50%"),
        
        (0.8, 0.15, 0.05, "MVRV 80% + RSI 15% + F&G 5%"),
        (0.7, 0.2, 0.1, "MVRV 70% + RSI 20% + F&G 10%"),  # 當前
        (0.7, 0.25, 0.05, "MVRV 70% + RSI 25% + F&G 5%"),
        (0.6, 0.3, 0.1, "MVRV 60% + RSI 30% + F&G 10%"),
        (0.6, 0.25, 0.15, "MVRV 60% + RSI 25% + F&G 15%"),
        
        (0.75, 0.2, 0.05, "MVRV 75% + RSI 20% + F&G 5%"),
        (0.65, 0.25, 0.1, "MVRV 65% + RSI 25% + F&G 10%"),
    ]
    
    results = []
    
    for mvrv_w, rsi_w, fg_w, name in weight_configs:
        strategy = WeightedStrategy(mvrv_w, rsi_w, fg_w, core_ratio=0.4)
        btc, cost = strategy.run(df)
        vs_hodl = ((btc / total_btc_hodl) - 1) * 100
        
        results.append({
            'name': name,
            'mvrv_w': mvrv_w,
            'rsi_w': rsi_w,
            'fg_w': fg_w,
            'btc': btc,
            'cost': cost,
            'vs_hodl': vs_hodl
        })
        
        print(f"✓ {name:<40} {btc:>10.4f} BTC ({vs_hodl:>+7.1f}%)")
    
    # 排序找出最佳
    results_sorted = sorted(results, key=lambda x: x['btc'], reverse=True)
    
    print("\n" + "="*80)
    print(" 🏆 Top 5 最佳配置")
    print("="*80)
    
    print(f"\n{'排名':<5} {'配置':<40} {'最終BTC':>12} {'vs HODL':>10} {'平均成本':>12}")
    print("-"*80)
    
    for i, r in enumerate(results_sorted[:5], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} #{i:<3} {r['name']:<40} {r['btc']:>12.6f} {r['vs_hodl']:>9.1f}% ${r['cost']:>11,.0f}")
    
    # 分析冠軍
    winner = results_sorted[0]
    print("\n" + "="*80)
    print(" 💡 最佳配置分析")
    print("="*80)
    
    print(f"\n🏆 冠軍：{winner['name']}")
    print(f"   權重：MVRV {winner['mvrv_w']*100:.0f}% + RSI {winner['rsi_w']*100:.0f}% + F&G {winner['fg_w']*100:.0f}%")
    print(f"   最終 BTC：{winner['btc']:.6f}")
    print(f"   vs HODL：+{winner['vs_hodl']:.1f}%")
    print(f"   平均成本：${winner['cost']:,.0f}")
    
    # 比較當前配置 (70/20/10)
    current = next((r for r in results if r['mvrv_w'] == 0.7 and r['rsi_w'] == 0.2 and r['fg_w'] == 0.1), None)
    if current:
        improvement = ((winner['btc'] / current['btc']) - 1) * 100
        print(f"\n📊 vs 當前配置 (70/20/10)：")
        if improvement > 0:
            print(f"   ✅ 改進 {improvement:+.2f}% ({winner['btc'] - current['btc']:.4f} BTC)")
        else:
            print(f"   當前配置已經很好！")
    
    # 洞察
    print(f"\n💡 洞察：")
    
    # 分析 MVRV 權重影響
    pure_mvrv = next((r for r in results if r['mvrv_w'] == 1.0), None)
    if pure_mvrv:
        print(f"\n   純 MVRV vs 最佳組合：")
        print(f"   - 純 MVRV：{pure_mvrv['btc']:.6f} BTC")
        print(f"   - 最佳組合：{winner['btc']:.6f} BTC")
        print(f"   - 差距：{((winner['btc'] / pure_mvrv['btc']) - 1) * 100:+.1f}%")
    
    # 建議
    print(f"\n📋 建議：")
    if winner['mvrv_w'] >= 0.7:
        print(f"   ✓ MVRV 應保持主導地位（≥70%）")
    if winner['rsi_w'] > 0.15:
        print(f"   ✓ RSI 提供重要補充信息（{winner['rsi_w']*100:.0f}%）")
    if winner['fg_w'] > 0:
        print(f"   ✓ F&G 有助於捕捉情緒極端（{winner['fg_w']*100:.0f}%）")
    else:
        print(f"   ⚠ F&G 似乎效果不明顯，可考慮移除")


if __name__ == '__main__':
    main()
