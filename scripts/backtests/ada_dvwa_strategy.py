#!/usr/bin/env python3
# scripts/backtests/ada_dvwa_strategy.py
"""
ADA 動態價值加權平均 (DVWA) 策略回測

基於專業報告的策略：
1. 使用 MVRV Z-Score（代理：BTC.D）和 RSI 作為動態乘數
2. 買入矩陣：在低估區加碼 2-3x
3. 分批賣出：區域 1-4 階梯式變現
4. 質押收益：2.4% APY 持續複利
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

INITIAL_CAPITAL = 10000
WEEKLY_INVESTMENT = 250
ADA_STAKING_APY = 0.024
TRADE_FEE = 0.001

def calculate_rsi(prices, period=14):
    """計算 RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_valuation_multiplier(btc_d):
    """
    估值乘數（使用 BTC.D 作為 MVRV 代理）
    
    MVRV 邏輯：
    - 極度低估（BTC.D > 65）→ 2.5-3.0x
    - 低估（BTC.D 55-65）→ 1.5-2.0x
    - 中性（BTC.D 45-55）→ 1.0x
    - 高估（BTC.D 40-45）→ 0.5x
    - 泡沫（BTC.D < 40）→ 0x（停止買入）
    """
    if btc_d > 65:
        return 2.5
    elif btc_d > 60:
        return 2.0
    elif btc_d > 55:
        return 1.5
    elif btc_d > 50:
        return 1.0
    elif btc_d > 45:
        return 0.5
    else:
        return 0.0

def get_momentum_multiplier(rsi):
    """
    動能乘數
    
    RSI 邏輯：
    - 極度超賣（< 30）→ 1.5x
    - 超賣（30-40）→ 1.2x
    - 中性（40-60）→ 1.0x
    - 超買（> 60）→ 0.8x
    """
    if rsi < 30:
        return 1.5
    elif rsi < 40:
        return 1.2
    elif rsi > 60:
        return 0.8
    else:
        return 1.0

def get_sell_zone(price, entry_avg, btc_d, rsi):
    """
    分批賣出邏輯（報告中的區域 1-4）
    
    區域 1：收回成本（漲幅 100-200%）→ 賣 10%
    區域 2：前高測試（漲幅 300-400%）→ 賣 25%
    區域 3：價格發現（漲幅 500%+）→ 賣 40%
    區域 4：狂熱泡沫（BTC.D < 38 或 RSI > 85）→ 清倉
    
    Returns:
        (should_sell, sell_ratio)
    """
    profit_pct = (price - entry_avg) / entry_avg * 100
    
    # 區域 4：極端泡沫
    if btc_d < 38 or rsi > 85:
        return True, 0.9  # 清倉保留 10%
    
    # 區域 3：價格發現（5 倍）
    if profit_pct > 400:
        return True, 0.4
    
    # 區域 2：重要阻力（3-4 倍）
    if profit_pct > 250:
        return True, 0.25
    
    # 區域 1：收回成本（1.5-2 倍）
    if profit_pct > 120:
        return True, 0.10
    
    return False, 0.0


class DVWAStrategy:
    def __init__(self, name):
        self.name = name
        self.df = None
        
        self.ada_holdings = 0.0
        self.cash = INITIAL_CAPITAL
        self.total_invested = INITIAL_CAPITAL
        
        self.staking_rewards = 0.0
        self.buy_count = 0
        self.sell_count = 0
        
        # 記錄買入成本
        self.purchases = []
        
    def load_data(self):
        """載入數據"""
        ada_df = pd.read_csv(DATA_DIR / "cardano_price.csv")
        ada_df['date'] = pd.to_datetime(ada_df['date'])
        ada_df.rename(columns={'price': 'ada_price'}, inplace=True)
        
        btc_d_df = pd.read_csv(DATA_DIR / "btc_dominance.csv")
        btc_d_df['date'] = pd.to_datetime(btc_d_df['date'])
        
        df = ada_df.merge(btc_d_df, on='date', how='left')
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # 計算每週 RSI
        df['rsi_weekly'] = calculate_rsi(df['ada_price'], period=14*7)  # 約 14 週
        
        self.df = df.sort_values('date').reset_index(drop=True)
        print(f"✅ 數據範圍: {len(self.df)} 天")
        
    def run_dvwa(self):
        """執行 DVWA 策略"""
        print(f"\n🔄 執行：{self.name}")
        
        for i in range(100, len(self.df), 7):  # 每週，從第 100 天開始
            row = self.df.iloc[i]
            date = row['date']
            ada_price = row['ada_price']
            btc_d = row.get('btc_dominance', 50)
            rsi = row.get('rsi_weekly', 50)
            
            # 每週質押收益
            weekly_reward = self.ada_holdings * (ADA_STAKING_APY / 52)
            self.ada_holdings += weekly_reward
            self.staking_rewards += weekly_reward
            
            # ===== 賣出邏輯（優先） =====
            if self.ada_holdings > 0 and len(self.purchases) > 0:
                avg_entry = sum(p['price'] * p['amount'] for p in self.purchases) / sum(p['amount'] for p in self.purchases)
                should_sell, sell_ratio = get_sell_zone(ada_price, avg_entry, btc_d, rsi)
                
                if should_sell:
                    sell_amount = self.ada_holdings * sell_ratio
                    sell_value = sell_amount * ada_price * (1 - TRADE_FEE)
                    
                    self.cash += sell_value
                    self.ada_holdings -= sell_amount
                    self.sell_count += 1
                    
                    # 移除對應比例的成本記錄
                    if sell_ratio >= 0.9:
                        self.purchases = []
                    else:
                        for p in self.purchases:
                            p['amount'] *= (1 - sell_ratio)
            
            # ===== 買入邏輯 =====
            val_multiplier = get_valuation_multiplier(btc_d)
            mom_multiplier = get_momentum_multiplier(rsi)
            
            final_multiplier = val_multiplier * mom_multiplier
            
            if final_multiplier > 0:
                invest_amount = WEEKLY_INVESTMENT * final_multiplier
                
                if self.cash >= invest_amount:
                    ada_bought = (invest_amount * (1 - TRADE_FEE)) / ada_price
                    self.ada_holdings += ada_bought
                    self.cash -= invest_amount
                    self.buy_count += 1
                    
                    self.purchases.append({
                        'date': date,
                        'price': ada_price,
                        'amount': ada_bought
                    })
    
    def get_stats(self):
        """計算統計"""
        last_price = self.df.iloc[-1]['ada_price']
        final_value = self.ada_holdings * last_price + self.cash
        roi_pct = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        
        return {
            'final_value': final_value,
            'ada_holdings': self.ada_holdings,
            'cash': self.cash,
            'roi_pct': roi_pct,
            'staking_rewards':self.staking_rewards,
            'buy_count': self.buy_count,
            'sell_count': self.sell_count
        }


def compare_strategies():
    """對比策略"""
    print("="*70)
    print("🧠 DVWA 策略 vs 其他策略對比")
    print("="*70)
    
    results = {}
    
    # DVWA 策略
    dvwa = DVWAStrategy("DVWA 策略")
    dvwa.load_data()
    dvwa.run_dvwa()
    results['DVWA'] = dvwa.get_stats()
    
    # 參考：固定 DCA
    fixed_dca = DVWAStrategy("固定 DCA（參考）")
    fixed_dca.load_data()
    # 簡化固定 DCA
    for i in range(0, len(fixed_dca.df), 7):
        row = fixed_dca.df.iloc[i]
        ada_price = row['ada_price']
        
        weekly_reward = fixed_dca.ada_holdings * (ADA_STAKING_APY / 52)
        fixed_dca.ada_holdings += weekly_reward
        fixed_dca.staking_rewards += weekly_reward
        
        if fixed_dca.cash >= WEEKLY_INVESTMENT:
            ada_bought = (WEEKLY_INVESTMENT * (1 - TRADE_FEE)) / ada_price
            fixed_dca.ada_holdings += ada_bought
            fixed_dca.cash -= WEEKLY_INVESTMENT
    
    results['固定 DCA'] = fixed_dca.get_stats()
    
    # 輸出對比
    print("\n" + "="*70)
    print("📊 策略績效對比")
    print("="*70)
    
    print(f"\n{'策略':<15} {'最終價值':>12} {'ROI %':>10} {'ADA':>12} {'買入':>6} {'賣出':>6}")
    print("-"*70)
    
    for name, stats in results.items():
        print(f"{name:<15} ${stats['final_value']:>11,.0f} {stats['roi_pct']:>9.1f}% "
              f"{stats['ada_holdings']:>11,.0f} {stats['buy_count']:>6} {stats['sell_count']:>6}")
    
    # DVWA 特殊統計
    dvwa_stats = results['DVWA']
    print(f"\n💡 DVWA 策略亮點：")
    print(f"   質押收益：{dvwa_stats['staking_rewards']:.2f} ADA")
    print(f"   賣出次數：{dvwa_stats['sell_count']}（分批變現）")
    print(f"   剩餘現金：${dvwa_stats['cash']:,.0f}（可用流動性）")
    
    # 儲存報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"ada_dvwa_{timestamp}.txt"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("ADA DVWA 策略回測報告\n")
        f.write("="*70 + "\n\n")
        
        f.write("策略配置：\n")
        f.write("- 估值乘數：基於 BTC Dominance（MVRV 代理）\n")
        f.write("- 動能乘數：基於每週 RSI\n")
        f.write("- 分批賣出：區域 1-4 階梯式變現\n")
        f.write("- 質押收益：2.4% APY\n\n")
        
        f.write("績效對比：\n")
        f.write(f"{'策略':<15} {'價值':>12} {'ROI %':>10} {'ADA':>12}\n")
        f.write("-"*70 + "\n")
        for name, stats in results.items():
            f.write(f"{name:<15} ${stats['final_value']:>11,.0f} {stats['roi_pct']:>9.1f}% "
                   f"{stats['ada_holdings']:>11,.0f}\n")
    
    print(f"\n📄 報告已儲存：{report_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = compare_strategies()
    except Exception as e:
        print(f"❌ 錯誤：{e}")
        import traceback
        traceback.print_exc()
