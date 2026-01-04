#!/usr/bin/env python3
# scripts/backtests/staged_selling_backtest.py
"""
階梯式賣出 vs 一次性賣出回測

對比策略：
1. 一次性賣出：Pi Cycle Top 交叉 → 清空交易倉
2. 階梯式賣出：MVRV 3.0/5.0/7.0 → 分批賣出
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

# ========== 配置 ==========
INITIAL_CAPITAL = 10000
WEEKLY_INVESTMENT = 250
CORE_RATIO = 0.4  # 40% 核心倉
TRADE_FEE = 0.001

def calculate_rsi(prices, period=14):
    """計算 RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_mvrv_proxy(prices, ma_200w):
    """
    MVRV 代理：價格 vs 200週 MA
    （缺少真實 MVRV 數據時使用）
    """
    return prices / ma_200w

def get_buy_multiplier(mvrv_proxy, rsi, fg):
    """買入倍數（與現有系統一致）"""
    # 簡化的綜合分數
    mvrv_score = min(100, max(0, mvrv_proxy * 30))
    composite_score = (mvrv_score * 0.65) + (rsi * 0.25) + (fg * 0.10)
    
    if composite_score < 15:
        return 3.5
    elif composite_score < 25:
        return 2.0
    elif composite_score < 35:
        return 1.5
    elif composite_score < 50:
        return 1.0
    elif composite_score < 60:
        return 0.5
    else:
        return 0.0


class SellingStrategy:
    def __init__(self, strategy_name, staged=False):
        self.strategy_name = strategy_name
        self.staged = staged
        self.df = None
        
        # 持倉
        self.core_btc = 0.0
        self.trade_btc = 0.0
        self.cash = INITIAL_CAPITAL
        
        # 統計
        self.total_invested = INITIAL_CAPITAL
        self.sell_log = []
        
    def load_data(self):
        """載入數據"""
        print(f"📥 載入數據（{self.strategy_name}）...")
        
        # BTC 價格
        btc_df = pd.read_csv(DATA_DIR / "bitcoin_price.csv")
        btc_df['date'] = pd.to_datetime(btc_df['date'])
        btc_df.rename(columns={'price': 'btc_price'}, inplace=True)
        
        # 計算技術指標
        btc_df['rsi'] = calculate_rsi(btc_df['btc_price'], period=14)
        btc_df['ma_200w'] = btc_df['btc_price'].rolling(window=200*7).mean()
        btc_df['mvrv_proxy'] = calculate_mvrv_proxy(btc_df['btc_price'], btc_df['ma_200w'])
        
        # 模擬 Fear & Greed（簡化）
        btc_df['fg'] = 50  # 預設值
        
        # 模擬 Pi Cycle（簡化：價格偏離 MA 過大）
        btc_df['pi_cycle_signal'] = (btc_df['btc_price'] / btc_df['ma_200w']) > 3.5
        
        self.df = btc_df.dropna().reset_index(drop=True)
        print(f"✅ 數據範圍: {len(self.df)} 天")
        
    def run_backtest(self):
        """執行回測"""
        print(f"\n🔄 執行：{self.strategy_name}")
        
        # 追蹤賣出狀態
        sold_zones = set()
        
        for i in range(0, len(self.df), 7):  # 每週
            row = self.df.iloc[i]
            date = row['date']
            btc_price = row['btc_price']
            mvrv_proxy = row.get('mvrv_proxy', 1.0)
            rsi = row.get('rsi', 50)
            fg = row.get('fg', 50)
            pi_cycle = row.get('pi_cycle_signal', False)
            
            # ===== 買入邏輯 =====
            multiplier = get_buy_multiplier(mvrv_proxy, rsi, fg)
            invest_amount = WEEKLY_INVESTMENT * multiplier
            
            if self.cash >= invest_amount and invest_amount > 0:
                btc_bought = (invest_amount * (1 - TRADE_FEE)) / btc_price
                self.core_btc += btc_bought * CORE_RATIO
                self.trade_btc += btc_bought * (1 - CORE_RATIO)
                self.cash -= invest_amount
            
            # ===== 賣出邏輯 =====
            if self.trade_btc > 0:
                if self.staged:
                    # 階梯式賣出
                    sell_executed = False
                    
                    # 區域 1：MVRV > 3.0
                    if mvrv_proxy > 3.0 and 'zone1' not in sold_zones:
                        sell_ratio = 0.15
                        sell_amount = self.trade_btc * sell_ratio
                        sell_value = sell_amount * btc_price * (1 - TRADE_FEE)
                        
                        self.cash += sell_value
                        self.trade_btc -= sell_amount
                        sold_zones.add('zone1')
                        sell_executed = True
                        
                        self.sell_log.append({
                            'date': date,
                            'zone': '區域 1',
                            'mvrv': mvrv_proxy,
                            'price': btc_price,
                            'btc_sold': sell_amount,
                            'value': sell_value
                        })
                    
                    # 區域 2：MVRV > 5.0
                    if mvrv_proxy > 5.0 and 'zone2' not in sold_zones:
                        sell_ratio = 0.30
                        sell_amount = self.trade_btc * sell_ratio
                        sell_value = sell_amount * btc_price * (1 - TRADE_FEE)
                        
                        self.cash += sell_value
                        self.trade_btc -= sell_amount
                        sold_zones.add('zone2')
                        sell_executed = True
                        
                        self.sell_log.append({
                            'date': date,
                            'zone': '區域 2',
                            'mvrv': mvrv_proxy,
                            'price': btc_price,
                            'btc_sold': sell_amount,
                            'value': sell_value
                        })
                    
                    # 區域 3：MVRV > 7.0 或 Pi Cycle
                    if (mvrv_proxy > 7.0 or pi_cycle) and 'zone3' not in sold_zones:
                        sell_amount = self.trade_btc  # 全部
                        sell_value = sell_amount * btc_price * (1 - TRADE_FEE)
                        
                        self.cash += sell_value
                        self.trade_btc = 0
                        sold_zones.add('zone3')
                        sell_executed = True
                        
                        self.sell_log.append({
                            'date': date,
                            'zone': '區域 3（清倉）',
                            'mvrv': mvrv_proxy,
                            'price': btc_price,
                            'btc_sold': sell_amount,
                            'value': sell_value
                        })
                
                else:
                    # 一次性賣出（Pi Cycle）
                    if pi_cycle and self.trade_btc > 0:
                        sell_amount = self.trade_btc
                        sell_value = sell_amount * btc_price * (1 - TRADE_FEE)
                        
                        self.cash += sell_value
                        self.trade_btc = 0
                        
                        self.sell_log.append({
                            'date': date,
                            'zone': 'Pi Cycle（一次性）',
                            'mvrv': mvrv_proxy,
                            'price': btc_price,
                            'btc_sold': sell_amount,
                            'value': sell_value
                        })
    
    def get_final_stats(self):
        """計算最終統計"""
        last_price = self.df.iloc[-1]['btc_price']
        
        btc_value = (self.core_btc + self.trade_btc) * last_price
        total_value = btc_value + self.cash
        
        total_btc = self.core_btc + self.trade_btc
        roi_pct = (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        
        # 計算賣出總額
        total_sold_value = sum(log['value'] for log in self.sell_log)
        
        return {
            'total_value': total_value,
            'total_btc': total_btc,
            'core_btc': self.core_btc,
            'trade_btc': self.trade_btc,
            'cash': self.cash,
            'roi_pct': roi_pct,
            'total_sold_value': total_sold_value,
            'sell_count': len(self.sell_log)
        }


def compare_strategies():
    """對比兩種策略"""
    print("="*70)
    print("📊 階梯式賣出 vs 一次性賣出回測")
    print("="*70)
    
    results = {}
    
    # 策略 1：一次性賣出（現有）
    s1 = SellingStrategy("一次性賣出（Pi Cycle）", staged=False)
    s1.load_data()
    s1.run_backtest()
    results['一次性賣出'] = s1.get_final_stats()
    
    # 策略 2：階梯式賣出（新）
    s2 = SellingStrategy("階梯式賣出（MVRV 區域）", staged=True)
    s2.load_data()
    s2.run_backtest()
    results['階梯式賣出'] = s2.get_final_stats()
    
    # 輸出對比
    print("\n" + "="*70)
    print("📊 策略績效對比")
    print("="*70)
    
    print(f"\n{'策略':<20} {'總價值':>12} {'ROI %':>10} {'BTC':>10} {'現金':>12}")
    print("-"*70)
    
    for name, stats in results.items():
        print(f"{name:<20} ${stats['total_value']:>11,.0f} {stats['roi_pct']:>9.1f}% "
              f"{stats['total_btc']:>9.4f} ${stats['cash']:>11,.0f}")
    
    # 詳細對比
    print(f"\n💰 賣出統計：")
    print(f"一次性賣出：")
    print(f"  賣出次數：{results['一次性賣出']['sell_count']}")
    print(f"  總賣出額：${results['一次性賣出']['total_sold_value']:,.0f}")
    
    print(f"\n階梯式賣出：")
    print(f"  賣出次數：{results['階梯式賣出']['sell_count']}")
    print(f"  總賣出額：${results['階梯式賣出']['total_sold_value']:,.0f}")
    
    # 賣出明細
    print(f"\n階梯式賣出明細：")
    for log in s2.sell_log:
        print(f"  {log['date'].date()} | {log['zone']} | ${log['price']:,.0f} | {log['btc_sold']:.6f} BTC → ${log['value']:,.0f}")
    
    # 判斷最佳策略
    best = max(results.items(), key=lambda x: x[1]['total_value'])
    diff_pct = (results['階梯式賣出']['total_value'] - results['一次性賣出']['total_value']) / results['一次性賣出']['total_value'] * 100
    
    print(f"\n🏆 最佳策略：{best[0]}")
    print(f"   總價值：${best[1]['total_value']:,.0f}")
    print(f"   差異：{diff_pct:+.2f}%")
    
    # 儲存報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"staged_selling_{timestamp}.txt"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("階梯式賣出 vs 一次性賣出回測報告\n")
        f.write("="*70 + "\n\n")
        f.write(f"回測期間：{s1.df['date'].min().date()} ~ {s1.df['date'].max().date()}\n\n")
        
        f.write("策略績效對比：\n")
        f.write(f"{'策略':<20} {'總價值':>12} {'ROI %':>10} {'BTC':>10} {'現金':>12}\n")
        f.write("-"*70 + "\n")
        for name, stats in results.items():
            f.write(f"{name:<20} ${stats['total_value']:>11,.0f} {stats['roi_pct']:>9.1f}% "
                   f"{stats['total_btc']:>9.4f} ${stats['cash']:>11,.0f}\n")
        
        f.write(f"\n最佳策略：{best[0]}\n")
        f.write(f"差異：{diff_pct:+.2f}%\n")
    
    print(f"\n📄 報告已儲存：{report_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = compare_strategies()
    except Exception as e:
        print(f"❌ 錯誤：{e}")
        import traceback
        traceback.print_exc()
