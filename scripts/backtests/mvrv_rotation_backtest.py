#!/usr/bin/env python3
# scripts/backtests/mvrv_rotation_backtest.py
"""
基於 MVRV/估值的 BTC/ADA 輪動策略回測

核心邏輯：
- BTC 低估 → 全力買 BTC
- BTC 正常 → 平衡配置
- BTC 過熱 → 轉向 ADA，賣出 BTC 交易倉

對比策略：
1. 純 BTC MVRV 策略（已知最佳）
2. 純 ADA + 質押
3. 固定 70/30
4. MVRV 輪動策略（新）
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from datetime import datetime

# 中文字型
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

sys.path.append(str(Path(__file__).parent.parent.parent))

# 路徑
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

# ========== 配置 ==========
INITIAL_CAPITAL = 10000
WEEKLY_INVESTMENT = 250
ADA_STAKING_APY = 0.024
ADA_CORE_RATIO = 0.10
BTC_CORE_RATIO = 0.40  # BTC 核心倉

# ========== MVRV 代理：綜合估值分數 ==========
def calculate_valuation_score(row):
    """
    計算 BTC 估值分數（0-100）
    
    使用：RSI + Fear & Greed（缺少 MVRV 數據時的代理）
    分數越低 = BTC 越低估
    """
    # 簡化版：使用 BTC Dominance 作為週期指標
    # 高 BTC.D = BTC 主導期 = 相對便宜
    # 低 BTC.D = 山寨季 = BTC 相對貴
    
    btc_d = row.get('btc_dominance', 50)
    
    # 反向映射：BTC.D 高 → 分數低（低估）
    # BTC.D 70% → 分數 20（極度低估）
    # BTC.D 40% → 分數 80（過熱）
    score = 100 - ((btc_d - 30) / 50 * 100)
    score = max(0, min(100, score))
    
    return score


def get_mvrv_rotation_ratio(score):
    """
    根據估值分數決定 BTC/ADA 配置比例
    
    Args:
        score: 估值分數 0-100（越低越便宜）
    
    Returns:
        (btc_ratio, ada_ratio)
    """
    if score < 20:  # 極度低估
        return 1.0, 0.0  # 100% BTC
    elif score < 40:  # 低估
        return 0.8, 0.2  # 80% BTC, 20% ADA
    elif score < 50:  # 正常
        return 0.7, 0.3  # 70% BTC, 30% ADA
    elif score < 60:  # 略高估
        return 0.5, 0.5  # 50/50
    elif score < 70:  # 高估
        return 0.3, 0.7  # 30% BTC, 70% ADA
    else:  # score >= 70，過熱
        return 0.0, 1.0  # 100% ADA


class MVRVRotationBacktest:
    def __init__(self, strategy_name):
        self.strategy_name = strategy_name
        self.df = None
        
        # BTC 持倉
        self.btc_core = 0.0
        self.btc_trading = 0.0
        self.btc_cash = 0.0
        
        # ADA 持倉
        self.ada_core = 0.0
        self.ada_trading = 0.0
        self.ada_cash = 0.0
        
        # 統計
        self.total_invested = INITIAL_CAPITAL
        self.ada_staking_rewards = 0.0
        self.btc_sold_profit = 0.0
        self.trade_log = []
        
    def load_data(self):
        """載入數據"""
        print(f"📥 載入數據...")
        
        btc_df = pd.read_csv(DATA_DIR / "bitcoin_price.csv")
        btc_df['date'] = pd.to_datetime(btc_df['date'])
        btc_df.rename(columns={'price': 'btc_price'}, inplace=True)
        
        ada_df = pd.read_csv(DATA_DIR / "cardano_price.csv")
        ada_df['date'] = pd.to_datetime(ada_df['date'])
        ada_df.rename(columns={'price': 'ada_price'}, inplace=True)
        
        btc_d_df = pd.read_csv(DATA_DIR / "btc_dominance.csv")
        btc_d_df['date'] = pd.to_datetime(btc_d_df['date'])
        
        df = btc_df.merge(ada_df, on='date', how='inner')
        df = df.merge(btc_d_df, on='date', how='left')
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # 計算估值分數
        df['valuation_score'] = df.apply(calculate_valuation_score, axis=1)
        
        self.df = df.sort_values('date').reset_index(drop=True)
        print(f"✅ 數據範圍: {len(self.df)} 天")
        
    def run_pure_btc(self):
        """策略 1：純 BTC（參考基準）"""
        print(f"\n🔄 執行：{self.strategy_name}")
        self.btc_cash = INITIAL_CAPITAL
        
        for i in range(0, len(self.df), 7):
            row = self.df.iloc[i]
            btc_price = row['btc_price']
            
            invest = WEEKLY_INVESTMENT
            if self.btc_cash >= invest:
                btc_bought = invest / btc_price
                self.btc_core += btc_bought * BTC_CORE_RATIO
                self.btc_trading += btc_bought * (1 - BTC_CORE_RATIO)
                self.btc_cash -= invest
    
    def run_pure_ada(self):
        """策略 2：純 ADA + 質押"""
        print(f"\n🔄 執行：{self.strategy_name}")
        self.ada_cash = INITIAL_CAPITAL
        
        for i in range(0, len(self.df), 7):
            row = self.df.iloc[i]
            ada_price = row['ada_price']
            
            # 質押收益
            total_ada = self.ada_core + self.ada_trading
            reward = total_ada * (ADA_STAKING_APY / 52)
            self.ada_core += reward * ADA_CORE_RATIO
            self.ada_trading += reward * (1 - ADA_CORE_RATIO)
            self.ada_staking_rewards += reward
            
            # 買入
            invest = WEEKLY_INVESTMENT
            if self.ada_cash >= invest:
                ada_bought = invest / ada_price
                self.ada_core += ada_bought * ADA_CORE_RATIO
                self.ada_trading += ada_bought * (1 - ADA_CORE_RATIO)
                self.ada_cash -= invest
    
    def run_fixed_7030(self):
        """策略 3：固定 70/30"""
        print(f"\n🔄 執行：{self.strategy_name}")
        self.btc_cash = INITIAL_CAPITAL * 0.7
        self.ada_cash = INITIAL_CAPITAL * 0.3
        
        for i in range(0, len(self.df), 7):
            row = self.df.iloc[i]
            btc_price = row['btc_price']
            ada_price = row['ada_price']
            
            # ADA 質押
            total_ada = self.ada_core + self.ada_trading
            reward = total_ada * (ADA_STAKING_APY / 52)
            self.ada_core += reward * ADA_CORE_RATIO
            self.ada_trading += reward * (1 - ADA_CORE_RATIO)
            self.ada_staking_rewards += reward
            
            # BTC
            btc_invest = WEEKLY_INVESTMENT * 0.7
            if self.btc_cash >= btc_invest:
                btc_bought = btc_invest / btc_price
                self.btc_core += btc_bought * BTC_CORE_RATIO
                self.btc_trading += btc_bought * (1 - BTC_CORE_RATIO)
                self.btc_cash -= btc_invest
            
            # ADA
            ada_invest = WEEKLY_INVESTMENT * 0.3
            if self.ada_cash >= ada_invest:
                ada_bought = ada_invest / ada_price
                self.ada_core += ada_bought * ADA_CORE_RATIO
                self.ada_trading += ada_bought * (1 - ADA_CORE_RATIO)
                self.ada_cash -= ada_invest
    
    def run_mvrv_rotation(self):
        """策略 4：MVRV 輪動（核心策略）"""
        print(f"\n🔄 執行：{self.strategy_name}")
        total_cash = INITIAL_CAPITAL
        
        for i in range(0, len(self.df), 7):
            row = self.df.iloc[i]
            date = row['date']
            btc_price = row['btc_price']
            ada_price = row['ada_price']
            score = row['valuation_score']
            
            # ADA 質押
            total_ada = self.ada_core + self.ada_trading
            reward = total_ada * (ADA_STAKING_APY / 52)
            self.ada_core += reward * ADA_CORE_RATIO
            self.ada_trading += reward * (1 - ADA_CORE_RATIO)
            self.ada_staking_rewards += reward
            
            # 動態配置
            btc_ratio, ada_ratio = get_mvrv_rotation_ratio(score)
            
            btc_invest = WEEKLY_INVESTMENT * btc_ratio
            ada_invest = WEEKLY_INVESTMENT * ada_ratio
            
            # BTC
            if btc_invest > 0 and total_cash >= btc_invest:
                btc_bought = btc_invest / btc_price
                self.btc_core += btc_bought * BTC_CORE_RATIO
                self.btc_trading += btc_bought * (1 - BTC_CORE_RATIO)
                total_cash -= btc_invest
                
                self.trade_log.append({
                    'date': date,
                    'type': 'BUY_BTC',
                    'value': btc_invest,
                    'score': score,
                    'ratio': btc_ratio
                })
            
            # ADA
            if ada_invest > 0 and total_cash >= ada_invest:
                ada_bought = ada_invest / ada_price
                self.ada_core += ada_bought * ADA_CORE_RATIO
                self.ada_trading += ada_bought * (1 - ADA_CORE_RATIO)
                total_cash -= ada_invest
                
                self.trade_log.append({
                    'date': date,
                    'type': 'BUY_ADA',
                    'value': ada_invest,
                    'score': score,
                    'ratio': ada_ratio
                })
            
            # 賣出邏輯：BTC 過熱時賣出交易倉
            if score > 75 and self.btc_trading > 0:
                sell_value = self.btc_trading * btc_price
                total_cash += sell_value
                self.btc_sold_profit += sell_value
                
                self.trade_log.append({
                    'date': date,
                    'type': 'SELL_BTC',
                    'value': sell_value,
                    'score': score
                })
                
                self.btc_trading = 0  # 清空交易倉
        
        self.btc_cash = total_cash / 2
        self.ada_cash = total_cash / 2
    
    def get_final_value(self):
        """計算最終價值"""
        last_row = self.df.iloc[-1]
        btc_price = last_row['btc_price']
        ada_price = last_row['ada_price']
        
        btc_value = (self.btc_core + self.btc_trading) * btc_price + self.btc_cash
        ada_value = (self.ada_core + self.ada_trading) * ada_price + self.ada_cash
        total_value = btc_value + ada_value
        
        return {
            'total_value': total_value,
            'btc_value': btc_value,
            'ada_value': ada_value,
            'btc_holdings': self.btc_core + self.btc_trading,
            'ada_holdings': self.ada_core + self.ada_trading,
            'staking_rewards': self.ada_staking_rewards,
            'btc_sold': self.btc_sold_profit,
            'roi_pct': (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        }


def compare_strategies():
    """對比所有策略"""
    print("="*70)
    print("🧠 基於估值的 BTC/ADA 輪動策略回測")
    print("="*70)
    
    results = {}
    
    # 策略 1
    s1 = MVRVRotationBacktest("純 BTC")
    s1.load_data()
    s1.run_pure_btc()
    results['純 BTC'] = s1.get_final_value()
    
    # 策略 2
    s2 = MVRVRotationBacktest("純 ADA")
    s2.load_data()
    s2.run_pure_ada()
    results['純 ADA'] = s2.get_final_value()
    
    # 策略 3
    s3 = MVRVRotationBacktest("固定 70/30")
    s3.load_data()
    s3.run_fixed_7030()
    results['固定 70/30'] = s3.get_final_value()
    
    # 策略 4：MVRV 輪動
    s4 = MVRVRotationBacktest("MVRV 輪動")
    s4.load_data()
    s4.run_mvrv_rotation()
    results['MVRV 輪動'] = s4.get_final_value()
    
    # 輸出報告
    print("\n" + "="*70)
    print("📊 策略績效對比（基於估值輪動）")
    print("="*70)
    
    print(f"\n{'策略':<15} {'總價值':>12} {'ROI %':>10} {'BTC':>10} {'ADA':>12}")
    print("-"*70)
    
    # 排序
    sorted_results = sorted(results.items(), key=lambda x: x[1]['total_value'], reverse=True)
    
    for idx, (name, result) in enumerate(sorted_results, 1):
        medal = ['🥇', '🥈', '🥉', '  '][min(idx-1, 3)]
        print(f"{medal} {name:<13} ${result['total_value']:>11,.0f} {result['roi_pct']:>9.1f}% "
              f"{result['btc_holdings']:>9.4f} {result['ada_holdings']:>11.0f}")
    
    # MVRV 輪動特殊統計
    mvrv_result = results['MVRV 輪動']
    print(f"\n💡 MVRV 輪動特殊統計：")
    print(f"   ADA 質押收益：{mvrv_result['staking_rewards']:.2f} ADA")
    if mvrv_result['btc_sold'] > 0:
        print(f"   BTC 賣出獲利：${mvrv_result['btc_sold']:,.0f}")
    
    # 儲存報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"mvrv_rotation_{timestamp}.txt"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("基於估值的 BTC/ADA 輪動策略回測\n")
        f.write("="*70 + "\n\n")
        f.write(f"回測期間：{s1.df['date'].min().date()} ~ {s1.df['date'].max().date()}\n\n")
        
        f.write("策略績效對比：\n")
        f.write(f"{'策略':<15} {'總價值':>12} {'ROI %':>10} {'BTC':>10} {'ADA':>12}\n")
        f.write("-"*70 + "\n")
        for idx, (name, result) in enumerate(sorted_results, 1):
            medal = ['🥇', '🥈', '🥉', '  '][min(idx-1, 3)]
            f.write(f"{medal} {name:<13} ${result['total_value']:>11,.0f} {result['roi_pct']:>9.1f}% "
                   f"{result['btc_holdings']:>9.4f} {result['ada_holdings']:>11.0f}\n")
    
    print(f"\n📄 報告已儲存：{report_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = compare_strategies()
    except Exception as e:
        print(f"❌ 錯誤：{e}")
        import traceback
        traceback.print_exc()
