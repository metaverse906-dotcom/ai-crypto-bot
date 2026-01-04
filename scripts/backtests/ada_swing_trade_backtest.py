#!/usr/bin/env python3
# scripts/backtests/ada_swing_trade_backtest.py
"""
ADA 波段交易策略回測

對比策略：
1. 固定 DCA（每週買入）
2. 波段交易（指標買入，高點賣出）
3. HODL（一次買入持有）

目標：找出最能累積 ADA 的策略
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from datetime import datetime

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

sys.path.append(str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

# ========== 配置 ==========
INITIAL_CAPITAL = 10000
WEEKLY_INVESTMENT = 250
ADA_STAKING_APY = 0.024
TRADE_FEE = 0.001  # 0.1% 手續費

# ========== 技術指標計算 ==========
def calculate_rsi(prices, period=14):
    """計算 RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ma(prices, period=20):
    """計算移動平均線"""
    return prices.rolling(window=period).mean()

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """計算布林通道"""
    ma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return upper, ma, lower


# ========== 波段交易信號 ==========
def get_swing_buy_signal(row):
    """
    波段買入信號（3 選 2）
    1. BTC.D > 55%
    2. ADA RSI < 35
    3. ADA 價格 < 20週均線
    """
    signals = 0
    
    if row.get('btc_dominance', 50) > 55:
        signals += 1
    
    if row.get('rsi', 50) < 35:
        signals += 1
    
    if row.get('ada_price', 0) < row.get('ma_20w', 0):
        signals += 1
    
    return signals >= 2

def get_swing_sell_signal(row, entry_price=None, current_holdings=0):
    """
    波段賣出信號（任一滿足）
    1. BTC.D < 45%（山寨季）
    2. ADA RSI > 65
    3. 獲利 > 80%
    4. 虧損 > -30%（止損）
    """
    if current_holdings == 0:
        return False, 0.0
    
    # 1. 山寨季
    if row.get('btc_dominance', 50) < 45:
        return True, 1.0  # 全賣
    
    # 2. 超買
    if row.get('rsi', 50) > 65:
        return True, 0.5  # 賣一半
    
    # 3. 止盈
    if entry_price and row.get('ada_price', 0) > 0:
        profit_pct = (row['ada_price'] - entry_price) / entry_price * 100
        if profit_pct > 80:
            return True, 0.7  # 賣 70%
    
    # 4. 止損
    if entry_price and row.get('ada_price', 0) > 0:
        profit_pct = (row['ada_price'] - entry_price) / entry_price * 100
        if profit_pct < -30:
            return True, 1.0  # 全賣止損
    
    return False, 0.0


class ADASwingTradeBacktest:
    def __init__(self, strategy_name):
        self.strategy_name = strategy_name
        self.df = None
        
        self.ada_holdings = 0.0
        self.cash = INITIAL_CAPITAL
        self.total_invested = INITIAL_CAPITAL
        
        self.staking_rewards = 0.0
        self.trade_count = 0
        self.win_count = 0
        self.trade_log = []
        
        # 波段交易專用
        self.avg_entry_price = 0.0
        self.positions = []  # 記錄每筆買入
        
    def load_data(self):
        """載入並準備數據"""
        print(f"📥 載入數據...")
        
        # ADA 價格
        ada_df = pd.read_csv(DATA_DIR / "cardano_price.csv")
        ada_df['date'] = pd.to_datetime(ada_df['date'])
        ada_df.rename(columns={'price': 'ada_price'}, inplace=True)
        
        # BTC Dominance
        btc_d_df = pd.read_csv(DATA_DIR / "btc_dominance.csv")
        btc_d_df['date'] = pd.to_datetime(btc_d_df['date'])
        
        # 合併
        df = ada_df.merge(btc_d_df, on='date', how='left')
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # 計算技術指標
        df['rsi'] = calculate_rsi(df['ada_price'], period=14)
        df['ma_20w'] = calculate_ma(df['ada_price'], period=140)  # 20週 ≈ 140天
        df['ma_50d'] = calculate_ma(df['ada_price'], period=50)
        
        upper, middle, lower = calculate_bollinger_bands(df['ada_price'], period=20)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        
        self.df = df.sort_values('date').reset_index(drop=True)
        print(f"✅ 數據範圍: {len(self.df)} 天")
        
    def run_fixed_dca(self):
        """策略 1：固定 DCA"""
        print(f"\n🔄 執行：{self.strategy_name}")
        
        for i in range(0, len(self.df), 7):  # 每週
            row = self.df.iloc[i]
            ada_price = row['ada_price']
            
            # 質押收益
            weekly_reward = self.ada_holdings * (ADA_STAKING_APY / 52)
            self.ada_holdings += weekly_reward
            self.staking_rewards += weekly_reward
            
            # 固定買入
            if self.cash >= WEEKLY_INVESTMENT:
                ada_bought = (WEEKLY_INVESTMENT * (1 - TRADE_FEE)) / ada_price
                self.ada_holdings += ada_bought
                self.cash -= WEEKLY_INVESTMENT
                self.trade_count += 1
    
    def run_swing_trade(self):
        """策略 2：波段交易"""
        print(f"\n🔄 執行：{self.strategy_name}")
        
        in_position = False
        
        for i in range(140, len(self.df)):  # 從 140 天後開始（等待 MA 計算完成）
            row = self.df.iloc[i]
            date = row['date']
            ada_price = row['ada_price']
            
            # 質押收益（持倉才質押）
            if self.ada_holdings > 0:
                daily_reward = self.ada_holdings * (ADA_STAKING_APY / 365)
                self.ada_holdings += daily_reward
                self.staking_rewards += daily_reward
            
            # 買入信號
            if not in_position and get_swing_buy_signal(row):
                invest_amount = min(self.cash, WEEKLY_INVESTMENT * 4)  # 最多 4 週的量
                
                if invest_amount >= WEEKLY_INVESTMENT:
                    ada_bought = (invest_amount * (1 - TRADE_FEE)) / ada_price
                    self.ada_holdings += ada_bought
                    self.cash -= invest_amount
                    
                    self.positions.append({
                        'entry_date': date,
                        'entry_price': ada_price,
                        'amount': ada_bought
                    })
                    
                    in_position = True
                    self.trade_count += 1
                    
                    self.trade_log.append({
                        'date': date,
                        'type': 'BUY',
                        'price': ada_price,
                        'amount': ada_bought,
                        'rsi': row['rsi'],
                        'btc_d': row['btc_dominance']
                    })
            
            # 賣出信號
            elif in_position and self.ada_holdings > 0:
                should_sell, sell_ratio = get_swing_sell_signal(
                    row, 
                    entry_price=self.positions[-1]['entry_price'] if self.positions else None,
                    current_holdings=self.ada_holdings
                )
                
                if should_sell:
                    sell_amount = self.ada_holdings * sell_ratio
                    sell_value = sell_amount * ada_price * (1 - TRADE_FEE)
                    
                    self.cash += sell_value
                    self.ada_holdings -= sell_amount
                    
                    # 計算勝率
                    if self.positions:
                        entry_price = self.positions[-1]['entry_price']
                        if ada_price > entry_price:
                            self.win_count += 1
                    
                    self.trade_log.append({
                        'date': date,
                        'type': 'SELL',
                        'price': ada_price,
                        'amount': sell_amount,
                        'value': sell_value,
                        'rsi': row['rsi'],
                        'btc_d': row['btc_dominance'],
                        'ratio': sell_ratio
                    })
                    
                    if sell_ratio >= 0.9:
                        in_position = False
    
    def run_hodl(self):
        """策略 3：HODL（一次性買入）"""
        print(f"\n🔄 執行：{self.strategy_name}")
        
        # 第一天全倉買入
        first_price = self.df.iloc[0]['ada_price']
        self.ada_holdings = (INITIAL_CAPITAL * (1 - TRADE_FEE)) / first_price
        self.cash = 0
        
        # 每天質押收益
        for i in range(len(self.df)):
            daily_reward = self.ada_holdings * (ADA_STAKING_APY / 365)
            self.ada_holdings += daily_reward
            self.staking_rewards += daily_reward
    
    def get_final_stats(self):
        """計算最終統計"""
        last_price = self.df.iloc[-1]['ada_price']
        final_value = self.ada_holdings * last_price + self.cash
        
        roi_pct = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        
        win_rate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        
        return {
            'final_value': final_value,
            'ada_holdings': self.ada_holdings,
            'cash': self.cash,
            'roi_pct': roi_pct,
            'staking_rewards': self.staking_rewards,
            'trade_count': self.trade_count,
            'win_rate': win_rate
        }


def compare_strategies():
    """對比三種策略"""
    print("="*70)
    print("📊 ADA 波段交易 vs DCA vs HODL")
    print("="*70)
    
    results = {}
    
    # 策略 1：固定 DCA
    s1 = ADASwingTradeBacktest("固定 DCA")
    s1.load_data()
    s1.run_fixed_dca()
    results['固定 DCA'] = s1.get_final_stats()
    
    # 策略 2：波段交易
    s2 = ADASwingTradeBacktest("波段交易")
    s2.load_data()
    s2.run_swing_trade()
    results['波段交易'] = s2.get_final_stats()
    
    # 策略 3：HODL
    s3 = ADASwingTradeBacktest("HODL")
    s3.load_data()
    s3.run_hodl()
    results['HODL'] = s3.get_final_stats()
    
    # 輸出對比
    print("\n" + "="*70)
    print("📊 策略績效對比")
    print("="*70)
    
    print(f"\n{'策略':<12} {'最終價值':>12} {'ROI %':>10} {'ADA 持倉':>12} {'交易次數':>10}")
    print("-"*70)
    
    sorted_results = sorted(results.items(), key=lambda x: x[1]['ada_holdings'], reverse=True)
    
    for idx, (name, stats) in enumerate(sorted_results, 1):
        medal = ['🥇', '🥈', '🥉'][min(idx-1, 2)]
        print(f"{medal} {name:<10} ${stats['final_value']:>11,.0f} {stats['roi_pct']:>9.1f}% "
              f"{stats['ada_holdings']:>11,.0f} {stats['trade_count']:>10}")
    
    # 波段交易特殊統計
    swing_stats = results['波段交易']
    print(f"\n💡 波段交易統計：")
    print(f"   交易次數：{swing_stats['trade_count']}")
    if swing_stats['trade_count'] > 0:
        print(f"   勝率：{swing_stats['win_rate']:.1f}%")
    print(f"   質押收益：{swing_stats['staking_rewards']:.2f} ADA")
    
    # 儲存報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"ada_swing_trade_{timestamp}.txt"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("ADA 波段交易策略回測\n")
        f.write("="*70 + "\n\n")
        f.write(f"回測期間：{s1.df['date'].min().date()} ~ {s1.df['date'].max().date()}\n\n")
        
        f.write("策略績效對比（依 ADA 累積量排序）：\n")
        f.write(f"{'策略':<12} {'最終價值':>12} {'ROI %':>10} {'ADA':>12} {'交易':>10}\n")
        f.write("-"*70 + "\n")
        
        for idx, (name, stats) in enumerate(sorted_results, 1):
            medal = ['🥇', '🥈', '🥉'][min(idx-1, 2)]
            f.write(f"{medal} {name:<10} ${stats['final_value']:>11,.0f} {stats['roi_pct']:>9.1f}% "
                   f"{stats['ada_holdings']:>11,.0f} {stats['trade_count']:>10}\n")
    
    print(f"\n📄 報告已儲存：{report_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = compare_strategies()
    except Exception as e:
        print(f"❌ 錯誤：{e}")
        import traceback
        traceback.print_exc()
