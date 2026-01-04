#!/usr/bin/env python3
# scripts/backtests/rotation_backtest.py
"""
BTC/ADA 輪動策略回測

對比策略：
1. 純 BTC DCA
2. 純 ADA DCA
3. 固定配置（70% BTC + 30% ADA）
4. 動態輪動（基於 BTC Dominance）

目標：找出最大化總價值的策略
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from datetime import datetime

# 中文字型設定
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

# 添加專案路徑
sys.path.append(str(Path(__file__).parent.parent.parent))

# 數據路徑
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

# ========== 策略配置 ==========
INITIAL_CAPITAL = 10000  # 初始資金
WEEKLY_INVESTMENT = 250  # 每週投資額

# ADA 質押配置
ADA_STAKING_APY = 0.024  # 2.4% 年化率
ADA_CORE_RATIO = 0.10    # 10% 核心倉

# BTC 策略（MVRV 加權，簡化版）
BTC_STRATEGY_MULTIPLIERS = {
    'extreme_low': 3.5,   # 極度低估
    'low': 2.0,           # 低估
    'normal': 1.0,        # 正常
    'high': 0.5,          # 高估
    'extreme_high': 0.0   # 極度高估
}

# ADA 策略（基於 BTC.D）
def get_ada_multiplier(btc_d):
    """根據 BTC Dominance 計算 ADA 買入倍數"""
    if btc_d > 65:
        return 3.0
    elif btc_d > 60:
        return 2.5
    elif btc_d > 55:
        return 2.0
    elif btc_d > 50:
        return 1.5
    elif btc_d > 45:
        return 1.0
    elif btc_d > 40:
        return 0.5
    else:
        return 0.0

# 輪動策略配置
def get_rotation_ratio(btc_d):
    """
    根據 BTC Dominance 計算 BTC/ADA 配置比例
    
    Returns:
        (btc_ratio, ada_ratio): 兩者總和為 1.0
    """
    # 方案 B：動態比例（線性映射）
    # BTC.D 40-70% 映射到 BTC 配置 0-100%
    btc_ratio = (btc_d - 40) / 30
    btc_ratio = max(0.0, min(1.0, btc_ratio))
    ada_ratio = 1.0 - btc_ratio
    
    return btc_ratio, ada_ratio


class RotationBacktest:
    def __init__(self, strategy_name):
        self.strategy_name = strategy_name
        self.df = None
        
        # BTC 持倉
        self.btc_holdings = 0.0
        self.btc_cash = INITIAL_CAPITAL
        
        # ADA 持倉
        self.ada_core = 0.0      # 核心倉（永不賣）
        self.ada_trading = 0.0   # 交易倉
        self.ada_cash = 0.0
        
        # 統計
        self.total_invested = INITIAL_CAPITAL
        self.ada_staking_rewards = 0.0
        self.trade_log = []
        
    def load_data(self):
        """載入所有必要數據"""
        print(f"📥 載入數據...")
        
        # BTC 價格
        btc_df = pd.read_csv(DATA_DIR / "bitcoin_price.csv")
        btc_df['date'] = pd.to_datetime(btc_df['date'])
        btc_df.rename(columns={'price': 'btc_price'}, inplace=True)
        
        # ADA 價格
        ada_df = pd.read_csv(DATA_DIR / "cardano_price.csv")
        ada_df['date'] = pd.to_datetime(ada_df['date'])
        ada_df.rename(columns={'price': 'ada_price'}, inplace=True)
        
        # BTC Dominance
        btc_d_df = pd.read_csv(DATA_DIR / "btc_dominance.csv")
        btc_d_df['date'] = pd.to_datetime(btc_d_df['date'])
        
        # 合併數據
        df = btc_df.merge(ada_df, on='date', how='inner')
        df = df.merge(btc_d_df, on='date', how='left')
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        self.df = df.sort_values('date').reset_index(drop=True)
        print(f"✅ 數據範圍: {len(self.df)} 天 ({self.df['date'].min().date()} - {self.df['date'].max().date()})")
        
    def run_strategy_pure_btc(self):
        """策略 1：純 BTC DCA（簡化 MVRV）"""
        print(f"\n🔄 執行策略：{self.strategy_name}")
        
        for i in range(0, len(self.df), 7):  # 每週
            row = self.df.iloc[i]
            date = row['date']
            btc_price = row['btc_price']
            
            # 簡化：固定 1.0x 倍數（可擴展為 MVRV 邏輯）
            invest_amount = WEEKLY_INVESTMENT * 1.0
            
            if self.btc_cash >= invest_amount:
                btc_bought = invest_amount / btc_price
                self.btc_holdings += btc_bought
                self.btc_cash -= invest_amount
                
                self.trade_log.append({
                    'date': date,
                    'type': 'BUY_BTC',
                    'amount': btc_bought,
                    'price': btc_price,
                    'value': invest_amount
                })
    
    def run_strategy_pure_ada(self):
        """策略 2：純 ADA DCA + 質押"""
        print(f"\n🔄 執行策略：{self.strategy_name}")
        
        # 初始化：全部資金給 ADA
        self.ada_cash = INITIAL_CAPITAL
        
        for i in range(0, len(self.df), 7):  # 每週
            row = self.df.iloc[i]
            date = row['date']
            ada_price = row['ada_price']
            btc_d = row['btc_dominance']
            
            # 質押收益（每週）
            total_ada = self.ada_core + self.ada_trading
            weekly_reward = total_ada * (ADA_STAKING_APY / 52)
            self.ada_core += weekly_reward * ADA_CORE_RATIO
            self.ada_trading += weekly_reward * (1 - ADA_CORE_RATIO)
            self.ada_staking_rewards += weekly_reward
            
            # 動態買入
            multiplier = get_ada_multiplier(btc_d)
            invest_amount = WEEKLY_INVESTMENT * multiplier
            
            if self.ada_cash >= invest_amount and invest_amount > 0:
                ada_bought = invest_amount / ada_price
                self.ada_core += ada_bought * ADA_CORE_RATIO
                self.ada_trading += ada_bought * (1 - ADA_CORE_RATIO)
                self.ada_cash -= invest_amount
                
                self.trade_log.append({
                    'date': date,
                    'type': 'BUY_ADA',
                    'amount': ada_bought,
                    'price': ada_price,
                    'value': invest_amount
                })
    
    def run_strategy_fixed_allocation(self, btc_pct=0.7):
        """策略 3：固定配置（例如 70% BTC + 30% ADA）"""
        print(f"\n🔄 執行策略：{self.strategy_name} ({btc_pct*100:.0f}% BTC)")
        
        # 初始化：按比例分配
        self.btc_cash = INITIAL_CAPITAL * btc_pct
        self.ada_cash = INITIAL_CAPITAL * (1 - btc_pct)
        
        for i in range(0, len(self.df), 7):
            row = self.df.iloc[i]
            date = row['date']
            btc_price = row['btc_price']
            ada_price = row['ada_price']
            
            # ADA 質押
            total_ada = self.ada_core + self.ada_trading
            weekly_reward = total_ada * (ADA_STAKING_APY / 52)
            self.ada_core += weekly_reward * ADA_CORE_RATIO
            self.ada_trading += weekly_reward * (1 - ADA_CORE_RATIO)
            self.ada_staking_rewards += weekly_reward
            
            # 固定比例投入
            btc_invest = WEEKLY_INVESTMENT * btc_pct
            ada_invest = WEEKLY_INVESTMENT * (1 - btc_pct)
            
            # BTC
            if self.btc_cash >= btc_invest:
                btc_bought = btc_invest / btc_price
                self.btc_holdings += btc_bought
                self.btc_cash -= btc_invest
            
            # ADA
            if self.ada_cash >= ada_invest:
                ada_bought = ada_invest / ada_price
                self.ada_core += ada_bought * ADA_CORE_RATIO
                self.ada_trading += ada_bought * (1 - ADA_CORE_RATIO)
                self.ada_cash -= ada_invest
    
    def run_strategy_rotation(self):
        """策略 4：動態輪動（基於 BTC.D）"""
        print(f"\n🔄 執行策略：{self.strategy_name}")
        
        # 初始化：全部資金池化
        total_cash = INITIAL_CAPITAL
        
        for i in range(0, len(self.df), 7):
            row = self.df.iloc[i]
            date = row['date']
            btc_price = row['btc_price']
            ada_price = row['ada_price']
            btc_d = row['btc_dominance']
            
            # ADA 質押
            total_ada = self.ada_core + self.ada_trading
            weekly_reward = total_ada * (ADA_STAKING_APY / 52)
            self.ada_core += weekly_reward * ADA_CORE_RATIO
            self.ada_trading += weekly_reward * (1 - ADA_CORE_RATIO)
            self.ada_staking_rewards += weekly_reward
            
            # 動態配置比例
            btc_ratio, ada_ratio = get_rotation_ratio(btc_d)
            
            btc_invest = WEEKLY_INVESTMENT * btc_ratio
            ada_invest = WEEKLY_INVESTMENT * ada_ratio
            
            # BTC
            if btc_invest > 0 and total_cash >= btc_invest:
                btc_bought = btc_invest / btc_price
                self.btc_holdings += btc_bought
                total_cash -= btc_invest
                
                self.trade_log.append({
                    'date': date,
                    'type': 'BUY_BTC',
                    'amount': btc_bought,
                    'price': btc_price,
                    'value': btc_invest,
                    'btc_d': btc_d,
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
                    'amount': ada_bought,
                    'price': ada_price,
                    'value': ada_invest,
                    'btc_d': btc_d,
                    'ratio': ada_ratio
                })
        
        # 最後剩餘現金平均分配（可選）
        self.btc_cash = total_cash / 2
        self.ada_cash = total_cash / 2
    
    def get_final_value(self):
        """計算最終總價值"""
        last_row = self.df.iloc[-1]
        btc_price = last_row['btc_price']
        ada_price = last_row['ada_price']
        
        btc_value = self.btc_holdings * btc_price + self.btc_cash
        ada_value = (self.ada_core + self.ada_trading) * ada_price + self.ada_cash
        
        total_value = btc_value + ada_value
        
        return {
            'total_value': total_value,
            'btc_value': btc_value,
            'ada_value': ada_value,
            'btc_holdings': self.btc_holdings,
            'ada_holdings': self.ada_core + self.ada_trading,
            'ada_core': self.ada_core,
            'ada_trading': self.ada_trading,
            'staking_rewards': self.ada_staking_rewards,
            'roi_pct': (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        }


def compare_strategies():
    """對比所有策略"""
    print("="*70)
    print("🔬 BTC/ADA 輪動策略回測對比")
    print("="*70)
    
    results = {}
    
    # 策略 1：純 BTC
    s1 = RotationBacktest("純 BTC DCA")
    s1.load_data()
    s1.run_strategy_pure_btc()
    results['純 BTC'] = s1.get_final_value()
    
    # 策略 2：純 ADA
    s2 = RotationBacktest("純 ADA DCA + 質押")
    s2.load_data()
    s2.run_strategy_pure_ada()
    results['純 ADA'] = s2.get_final_value()
    
    # 策略 3：固定配置 70/30
    s3 = RotationBacktest("固定配置 70/30")
    s3.load_data()
    s3.run_strategy_fixed_allocation(btc_pct=0.7)
    results['固定 70/30'] = s3.get_final_value()
    
    # 策略 4：動態輪動
    s4 = RotationBacktest("動態輪動")
    s4.load_data()
    s4.run_strategy_rotation()
    results['動態輪動'] = s4.get_final_value()
    
    # 輸出對比報告
    print("\n" + "="*70)
    print("📊 策略績效對比")
    print("="*70)
    
    print(f"\n{'策略':<15} {'總價值':>12} {'ROI %':>10} {'BTC 持倉':>12} {'ADA 持倉':>12}")
    print("-"*70)
    
    for name, result in results.items():
        print(f"{name:<15} ${result['total_value']:>11,.0f} {result['roi_pct']:>9.1f}% "
              f"{result['btc_holdings']:>11.4f} {result['ada_holdings']:>11.2f}")
    
    # 質押收益統計
    print("\n📈 ADA 質押收益：")
    for name in ['純 ADA', '固定 70/30', '動態輪動']:
        if name in results:
            print(f"   {name}: {results[name]['staking_rewards']:.2f} ADA")
    
    # 找出最佳策略
    best_strategy = max(results.items(), key=lambda x: x[1]['total_value'])
    print(f"\n🏆 最佳策略：{best_strategy[0]}")
    print(f"   最終價值：${best_strategy[1]['total_value']:,.0f}")
    print(f"   總報酬率：{best_strategy[1]['roi_pct']:.1f}%")
    
    # 儲存報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"rotation_comparison_{timestamp}.txt"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("BTC/ADA 輪動策略回測對比\n")
        f.write("="*70 + "\n\n")
        f.write(f"回測期間：{s1.df['date'].min().date()} ~ {s1.df['date'].max().date()}\n")
        f.write(f"初始資金：${INITIAL_CAPITAL:,}\n")
        f.write(f"每週投入：${WEEKLY_INVESTMENT}\n\n")
        
        f.write("策略績效對比：\n")
        f.write(f"{'策略':<15} {'總價值':>12} {'ROI %':>10} {'BTC':>12} {'ADA':>12}\n")
        f.write("-"*70 + "\n")
        for name, result in results.items():
            f.write(f"{name:<15} ${result['total_value']:>11,.0f} {result['roi_pct']:>9.1f}% "
                   f"{result['btc_holdings']:>11.4f} {result['ada_holdings']:>11.2f}\n")
        
        f.write(f"\n最佳策略：{best_strategy[0]}\n")
    
    print(f"\n📄 報告已儲存：{report_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = compare_strategies()
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
