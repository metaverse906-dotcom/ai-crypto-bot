#!/usr/bin/env python3
"""
完整策略對比：加權分數 vs 雙重確認 vs 純MVRV

策略 A：純 MVRV（基準）
策略 B：MVRV + RSI 雙重確認
策略 C：加權分數系統（MVRV 主導 + F&G/RSI 調整）
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

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def download_data():
    """下載並計算所有指標"""
    print("📥 下載數據並計算指標...")
    exchange = ccxt.binance()
    
    ohlcv = exchange.fetch_ohlcv(
        'BTC/USDT',
        timeframe='1w',
        since=int(datetime(2020, 1, 1).timestamp() * 1000),
        limit=1000
    )
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 技術指標
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
    
    # 簡化的 F&G（用動量推估，真實應該用歷史API）
    df['momentum'] = df['close'].pct_change(4)  # 4週動量
    df['fg_proxy'] = 50 + df['momentum'] * 100  # 簡化映射
    df['fg_proxy'] = df['fg_proxy'].clip(0, 100)
    
    print(f"✅ 完成：{len(df)} 週數據")
    return df


class StrategyA_PureMVRV:
    """策略 A：純 MVRV"""
    
    def __init__(self, core_ratio=0.4):
        self.core_ratio = core_ratio
        self.base_weekly = 250
        self.pm = PositionManager(core_ratio=core_ratio, data_file=None)
        self.cash = 0
        
    def get_buy_multiplier(self, mvrv):
        if mvrv < 0.1:
            return 3.0
        elif mvrv < 1.0:
            return 1.5
        elif mvrv < 5.0:
            return 1.0
        elif mvrv < 6.0:
            return 0.5
        else:
            return 0.0
    
    def get_sell_pct(self, mvrv):
        if mvrv < 6.0:
            return 0.0
        elif mvrv < 7.0:
            return 0.10
        elif mvrv < 9.0:
            return 0.30
        else:
            return 1.0
    
    def execute_week(self, price, mvrv):
        # 買入
        multiplier = self.get_buy_multiplier(mvrv)
        if multiplier > 0:
            buy_usd = self.base_weekly * multiplier
            buy_btc = buy_usd / price
            self.pm.add_buy(buy_btc, price, f"MVRV={mvrv:.2f}")
            self.cash -= buy_usd
        
        # 賣出
        sell_pct = self.get_sell_pct(mvrv)
        if sell_pct > 0:
            stats = self.pm.get_stats()
            if stats['trade_btc'] > 0:
                sell_btc = stats['trade_btc'] * sell_pct
                try:
                    result = self.pm.execute_sell_hifo(sell_btc, price)
                    self.cash += result['total_revenue']
                except:
                    pass
    
    def run(self, df):
        for idx, row in df.iterrows():
            if pd.notna(row['mvrv']):
                self.execute_week(row['close'], row['mvrv'])
        
        stats = self.pm.get_stats()
        return stats['total_btc'], stats['avg_cost']


class StrategyB_DualConfirm:
    """策略 B：MVRV + RSI 雙重確認"""
    
    def __init__(self, core_ratio=0.4):
        self.core_ratio = core_ratio
        self.base_weekly = 250
        self.pm = PositionManager(core_ratio=core_ratio, data_file=None)
        self.cash = 0
    
    def get_buy_multiplier(self, mvrv, rsi):
        # 雙重確認才加碼
        if mvrv < 0.1 and rsi < 30:
            return 3.0
        elif mvrv < 1.0 and rsi < 40:
            return 1.5
        elif mvrv < 5.0:
            return 1.0
        elif mvrv < 6.0:
            return 0.5
        else:
            return 0.0
    
    def get_sell_pct(self, mvrv, rsi):
        # 雙重過熱才賣
        if mvrv > 7.0 and rsi > 75:
            return 0.30
        elif mvrv > 6.5 and rsi > 70:
            return 0.10
        elif mvrv > 9.0:  # MVRV 極高不管 RSI
            return 1.0
        else:
            return 0.0
    
    def execute_week(self, price, mvrv, rsi):
        multiplier = self.get_buy_multiplier(mvrv, rsi)
        if multiplier > 0:
            buy_usd = self.base_weekly * multiplier
            buy_btc = buy_usd / price
            self.pm.add_buy(buy_btc, price, f"MVRV={mvrv:.2f},RSI={rsi:.0f}")
            self.cash -= buy_usd
        
        sell_pct = self.get_sell_pct(mvrv, rsi)
        if sell_pct > 0:
            stats = self.pm.get_stats()
            if stats['trade_btc'] > 0:
                sell_btc = stats['trade_btc'] * sell_pct
                try:
                    result = self.pm.execute_sell_hifo(sell_btc, price)
                    self.cash += result['total_revenue']
                except:
                    pass
    
    def run(self, df):
        for idx, row in df.iterrows():
            if pd.notna(row['mvrv']) and pd.notna(row['rsi']):
                self.execute_week(row['close'], row['mvrv'], row['rsi'])
        
        stats = self.pm.get_stats()
        return stats['total_btc'], stats['avg_cost']


class StrategyC_WeightedScore:
    """策略 C：加權分數系統（MVRV 主導 + F&G/RSI 微調）"""
    
    def __init__(self, core_ratio=0.4):
        self.core_ratio = core_ratio
        self.base_weekly = 250
        self.pm = PositionManager(core_ratio=core_ratio, data_file=None)
        self.cash = 0
    
    def calculate_composite_score(self, mvrv, rsi, fg):
        """
        計算綜合分數（0-100）
        - MVRV 權重 70%（主導）
        - RSI 權重 20%
        - F&G 權重 10%
        
        分數越低 = 越該買入
        分數越高 = 越該賣出
        """
        # MVRV 映射到 0-100
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
        
        # RSI 已經是 0-100
        rsi_score = rsi if not pd.isna(rsi) else 50
        
        # F&G 已經是 0-100
        fg_score = fg if not pd.isna(fg) else 50
        
        # 加權組合
        composite = (mvrv_score * 0.7) + (rsi_score * 0.2) + (fg_score * 0.1)
        
        return composite
    
    def get_buy_multiplier(self, score):
        """
        根據綜合分數決定買入倍數
        分數越低，買入越多
        """
        if score < 15:  # 極度低估
            return 3.5  # 比純 MVRV 更激進
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
        """
        根據綜合分數決定賣出比例
        分數越高，賣出越多
        """
        if score < 70:
            return 0.0
        elif score < 80:  # 開始過熱
            return 0.10
        elif score < 90:  # 明顯過熱
            return 0.30
        elif score < 95:  # 極度過熱
            return 0.50
        else:  # 泡沫
            return 1.0
    
    def execute_week(self, price, mvrv, rsi, fg):
        score = self.calculate_composite_score(mvrv, rsi, fg)
        
        # 買入
        multiplier = self.get_buy_multiplier(score)
        if multiplier > 0:
            buy_usd = self.base_weekly * multiplier
            buy_btc = buy_usd / price
            self.pm.add_buy(buy_btc, price, f"Score={score:.0f}")
            self.cash -= buy_usd
        
        # 賣出
        sell_pct = self.get_sell_pct(score)
        if sell_pct > 0:
            stats = self.pm.get_stats()
            if stats['trade_btc'] > 0:
                sell_btc = stats['trade_btc'] * sell_pct
                try:
                    result = self.pm.execute_sell_hifo(sell_btc, price)
                    self.cash += result['total_revenue']
                except:
                    pass
    
    def run(self, df):
        for idx, row in df.iterrows():
            if pd.notna(row['mvrv']):
                self.execute_week(
                    row['close'], 
                    row['mvrv'], 
                    row['rsi'] if pd.notna(row['rsi']) else 50,
                    row['fg_proxy'] if pd.notna(row['fg_proxy']) else 50
                )
        
        stats = self.pm.get_stats()
        return stats['total_btc'], stats['avg_cost']


def main():
    print("\n" + "="*80)
    print(" 三策略終極對決：純MVRV vs 雙重確認 vs 加權分數")
    print("="*80)
    
    df = download_data()
    
    print(f"\n測試期間：{df['date'].min().date()} → {df['date'].max().date()}")
    print(f"週數：{len(df)}")
    print(f"起始價格：${df.iloc[0]['close']:,.0f}")
    print(f"最終價格：${df.iloc[-1]['close']:,.0f}")
    
    # HODL 基準
    print("\n" + "="*80)
    print(" 執行回測...")
    print("="*80)
    
    total_btc_hodl = sum(250 / row['close'] for idx, row in df.iterrows() if pd.notna(row['close']))
    final_price = df.iloc[-1]['close']
    
    results = {
        'HODL': {
            'btc': total_btc_hodl,
            'cost': (250 * len(df)) / total_btc_hodl
        }
    }
    
    # 策略 A
    print("▶ 策略 A：純 MVRV...")
    strategy_a = StrategyA_PureMVRV(core_ratio=0.4)
    btc_a, cost_a = strategy_a.run(df)
    results['A_PureMVRV'] = {'btc': btc_a, 'cost': cost_a}
    
    # 策略 B
    print("▶ 策略 B：MVRV+RSI 雙重確認...")
    strategy_b = StrategyB_DualConfirm(core_ratio=0.4)
    btc_b, cost_b = strategy_b.run(df)
    results['B_DualConfirm'] = {'btc': btc_b, 'cost': cost_b}
    
    # 策略 C
    print("▶ 策略 C：加權分數...")
    strategy_c = StrategyC_WeightedScore(core_ratio=0.4)
    btc_c, cost_c = strategy_c.run(df)
    results['C_WeightedScore'] = {'btc': btc_c, 'cost': cost_c}
    
    # 結果對比
    print("\n" + "="*80)
    print(" 📊 最終對決結果")
    print("="*80)
    
    print(f"\n{'策略':<25} {'最終BTC':>15} {'vs HODL':>12} {'平均成本':>15}")
    print("-"*80)
    
    for name, data in results.items():
        vs_hodl = ((data['btc'] / results['HODL']['btc']) - 1) * 100
        emoji = ""
        if name == 'HODL':
            emoji = "📈"
        elif vs_hodl > 150:
            emoji = "🏆"
        elif vs_hodl > 100:
            emoji = "🥇"
        elif vs_hodl > 50:
            emoji = "🥈"
        
        print(f"{emoji} {name:<23} {data['btc']:>15.6f} {vs_hodl:>11.1f}% ${data['cost']:>14,.0f}")
    
    # 找出冠軍
    print("\n" + "="*80)
    print(" 🏆 勝者分析")
    print("="*80)
    
    strategies = ['A_PureMVRV', 'B_DualConfirm', 'C_WeightedScore']
    winner = max(strategies, key=lambda s: results[s]['btc'])
    winner_btc = results[winner]['btc']
    
    print(f"\n🥇 冠軍：{winner}")
    print(f"   最終 BTC：{winner_btc:.6f}")
    print(f"   vs HODL：+{((winner_btc / results['HODL']['btc']) - 1) * 100:.1f}%")
    
    print(f"\n📊 詳細比較：")
    for s in strategies:
        btc_diff = results[s]['btc'] - results['HODL']['btc']
        btc_pct = ((results[s]['btc'] / results['HODL']['btc']) - 1) * 100
        cost_saving = results['HODL']['cost'] - results[s]['cost']
        
        label = "✅" if s == winner else "  "
        print(f"{label} {s:<20} 多累積 {btc_diff:>8.4f} BTC (+{btc_pct:>6.1f}%) | 成本降低 ${cost_saving:>6,.0f}")
    
    # 策略特性總結
    print(f"\n💡 策略特性：")
    print(f"\n策略 A (純MVRV)：")
    print(f"  ✓ 簡單直觀，只看鏈上估值")
    print(f"  ✓ 適合長期穩健投資者")
    print(f"  ✗ 可能錯過短期極端機會")
    
    print(f"\n策略 B (雙重確認)：")
    print(f"  ✓ 降低誤判風險")
    print(f"  ✓ 在極端情況更激進")
    print(f"  ✗ 可能延遲買賣時機")
    
    print(f"\n策略 C (加權分數)：")
    print(f"  ✓ 綜合多個維度，更細膩")
    print(f"  ✓ MVRV 主導但接受其他輔助")
    print(f"  ✓ 可以動態調整權重")
    print(f"  ✗ 稍微複雜一些")


if __name__ == '__main__':
    main()
