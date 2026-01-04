#!/usr/bin/env python3
# scripts/backtests/ada_hybrid_optimized.py
"""
ADA 混合策略優化回測

策略：60% 固定 DCA + 40% 波段加碼
目標：測試多種買入賣出參數，找出最佳組合
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
from itertools import product

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

def calculate_ma(prices, period=20):
    """計算移動平均線"""
    return prices.rolling(window=period).mean()


class HybridStrategy:
    def __init__(self, params):
        """
        params = {
            'fixed_ratio': 0.6,        # 固定 DCA 比例
            'buy_btc_d': 55,          # BTC.D 買入閾值
            'buy_rsi': 45,            # RSI 買入閾值
            'sell_btc_d': 42,         # BTC.D 賣出閾值  
            'sell_rsi': 70,           # RSI 賣出閾值
            'sell_profit': 100,       # 獲利賣出%
            'keep_ratio': 0.5         # 賣出時保留比例
        }
        """
        self.params = params
        self.df = None
        
        # 固定 DCA 部分
        self.fixed_ada = 0.0
        self.fixed_cash = INITIAL_CAPITAL * params['fixed_ratio']
        
        # 波段交易部分
        self.swing_ada = 0.0
        self.swing_cash = INITIAL_CAPITAL * (1 - params['fixed_ratio'])
        
        self.staking_rewards = 0.0
        self.trade_count = 0
        self.swing_positions = []
        
    def load_data(self):
        """載入數據"""
        ada_df = pd.read_csv(DATA_DIR / "cardano_price.csv")
        ada_df['date'] = pd.to_datetime(ada_df['date'])
        ada_df.rename(columns={'price': 'ada_price'}, inplace=True)
        
        btc_d_df = pd.read_csv(DATA_DIR / "btc_dominance.csv")
        btc_d_df['date'] = pd.to_datetime(btc_d_df['date'])
        
        df = ada_df.merge(btc_d_df, on='date', how='left')
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        df['rsi'] = calculate_rsi(df['ada_price'], period=14)
        df['ma_50'] = calculate_ma(df['ada_price'], period=50)
        
        self.df = df.sort_values('date').reset_index(drop=True)
        
    def run(self):
        """執行混合策略"""
        for i in range(50, len(self.df)):  # 從第 50 天開始（等 RSI 計算完成）
            row = self.df.iloc[i]
            date = row['date']
            ada_price = row['ada_price']
            btc_d = row.get('btc_dominance', 50)
            rsi = row.get('rsi', 50)
            
            # 每天質押收益
            total_ada = self.fixed_ada + self.swing_ada
            daily_reward = total_ada * (ADA_STAKING_APY / 365)
            
            # 質押獎勵按比例分配
            if total_ada > 0:
                fixed_reward = daily_reward * (self.fixed_ada / total_ada)
                swing_reward = daily_reward * (self.swing_ada / total_ada)
                self.fixed_ada += fixed_reward
                self.swing_ada += swing_reward
                self.staking_rewards += daily_reward
            
            # ===== 固定 DCA 部分（每週） =====
            if i % 7 == 0:
                fixed_invest = WEEKLY_INVESTMENT * self.params['fixed_ratio']
                if self.fixed_cash >= fixed_invest:
                    ada_bought = (fixed_invest * (1 - TRADE_FEE)) / ada_price
                    self.fixed_ada += ada_bought
                    self.fixed_cash -= fixed_invest
            
            # ===== 波段加碼部分（每週檢查） =====
            if i % 7 == 0:
                # 買入信號
                buy_signal = (
                    btc_d > self.params['buy_btc_d'] or 
                    rsi < self.params['buy_rsi']
                )
                
                if buy_signal:
                    swing_invest = WEEKLY_INVESTMENT * (1 - self.params['fixed_ratio'])
                    
                    # 如果同時滿足兩個條件，雙倍加碼
                    if btc_d > self.params['buy_btc_d'] and rsi < self.params['buy_rsi']:
                        swing_invest *= 2
                    
                    if self.swing_cash >= swing_invest:
                        ada_bought = (swing_invest * (1 - TRADE_FEE)) / ada_price
                        self.swing_ada += ada_bought
                        self.swing_cash -= swing_invest
                        
                        self.swing_positions.append({
                            'entry_price': ada_price,
                            'amount': ada_bought,
                            'date': date
                        })
                        self.trade_count += 1
                
                # 賣出信號
                if self.swing_ada > 0:
                    sell_signal = False
                    sell_ratio = 0.0
                    
                    # 1. 山寨季高峰
                    if btc_d < self.params['sell_btc_d']:
                        sell_signal = True
                        sell_ratio = 1 - self.params['keep_ratio']  # 賣出但保留一部分
                    
                    # 2. 超買
                    elif rsi > self.params['sell_rsi']:
                        sell_signal = True
                        sell_ratio = 0.3  # 只賣 30%
                    
                    # 3. 大幅獲利
                    elif self.swing_positions:
                        avg_entry = sum(p['entry_price'] * p['amount'] for p in self.swing_positions) / sum(p['amount'] for p in self.swing_positions)
                        profit_pct = (ada_price - avg_entry) / avg_entry * 100
                        
                        if profit_pct > self.params['sell_profit']:
                            sell_signal = True
                            sell_ratio = 0.5  # 賣 50%
                    
                    if sell_signal and sell_ratio > 0:
                        sell_amount = self.swing_ada * sell_ratio
                        sell_value = sell_amount * ada_price * (1 - TRADE_FEE)
                        
                        self.swing_cash += sell_value
                        self.swing_ada -= sell_amount
        
    def get_stats(self):
        """計算最終統計"""
        last_price = self.df.iloc[-1]['ada_price']
        
        fixed_value = self.fixed_ada * last_price + self.fixed_cash
        swing_value = self.swing_ada * last_price + self.swing_cash
        total_value = fixed_value + swing_value
        
        total_ada = self.fixed_ada + self.swing_ada
        roi_pct = (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        
        return {
            'total_value': total_value,
            'total_ada': total_ada,
            'roi_pct': roi_pct,
            'staking_rewards': self.staking_rewards,
            'trade_count': self.trade_count,
            'fixed_ada': self.fixed_ada,
            'swing_ada': self.swing_ada
        }


def optimize_parameters():
    """優化參數組合"""
    print("="*70)
    print("🔬 ADA 混合策略參數優化")
    print("="*70)
    
    # 參數範圍
    param_grid = {
        'fixed_ratio': [0.5, 0.6, 0.7],           # 固定 DCA 比例
        'buy_btc_d': [50, 55, 60],                # BTC.D 買入閾值
        'buy_rsi': [40, 45, 50],                  # RSI 買入閾值
        'sell_btc_d': [40, 42, 45],               # BTC.D 賣出閾值
        'sell_rsi': [65, 70, 75],                 # RSI 賣出閾值
        'sell_profit': [80, 100, 120],            # 獲利賣出%
        'keep_ratio': [0.3, 0.5, 0.7]             # 賣出時保留比例
    }
    
    # 固定一些參數，只優化關鍵參數（減少計算量）
    best_result = None
    best_params = None
    top_results = []
    
    # 簡化：只測試部分關鍵組合
    test_configs = [
        # 格式：(fixed_ratio, buy_btc_d, buy_rsi, sell_btc_d, sell_rsi, sell_profit, keep_ratio)
        (0.6, 55, 45, 42, 70, 100, 0.5),  # 基準配置
        (0.6, 60, 40, 40, 70, 100, 0.5),  # 較嚴格買入
        (0.6, 50, 50, 42, 70, 100, 0.5),  # 較寬鬆買入
        (0.6, 55, 45, 45, 75, 120, 0.7),  # 較保守賣出
        (0.6, 55, 45, 40, 65, 80, 0.3),   # 較激進賣出
        (0.5, 55, 45, 42, 70, 100, 0.5),  # 50/50 配置
        (0.7, 55, 45, 42, 70, 100, 0.5),  # 70/30 配置
    ]
    
    print(f"\n測試 {len(test_configs)} 種參數組合...")
    
    for idx, config in enumerate(test_configs, 1):
        params = {
            'fixed_ratio': config[0],
            'buy_btc_d': config[1],
            'buy_rsi': config[2],
            'sell_btc_d': config[3],
            'sell_rsi': config[4],
            'sell_profit': config[5],
            'keep_ratio': config[6]
        }
        
        strategy = HybridStrategy(params)
        strategy.load_data()
        strategy.run()
        stats = strategy.get_stats()
        
        result = {
            'params': params,
            'stats': stats
        }
        
        top_results.append(result)
        
        if best_result is None or stats['total_ada'] > best_result['stats']['total_ada']:
            best_result = result
            best_params = params
        
        print(f"  配置 {idx}: ADA {stats['total_ada']:,.0f} | ROI {stats['roi_pct']:.1f}%")
    
    # 輸出最佳結果
    print("\n" + "="*70)
    print("🏆 最佳參數組合")
    print("="*70)
    
    print(f"\n參數配置：")
    for key, value in best_params.items():
        print(f"  {key}: {value}")
    
    print(f"\n績效表現：")
    best_stats = best_result['stats']
    print(f"  最終價值：${best_stats['total_value']:,.0f}")
    print(f"  總 ADA：{best_stats['total_ada']:,.0f}")
    print(f"  ROI：{best_stats['roi_pct']:.1f}%")
    print(f"  質押收益：{best_stats['staking_rewards']:.2f} ADA")
    print(f"  交易次數：{best_stats['trade_count']}")
    
    # 對比前三名
    print("\n" + "="*70)
    print("📊 Top 3 配置對比")
    print("="*70)
    
    top_3 = sorted(top_results, key=lambda x: x['stats']['total_ada'], reverse=True)[:3]
    
    for idx, result in enumerate(top_3, 1):
        params = result['params']
        stats = result['stats']
        print(f"\n{idx}. 固定 {params['fixed_ratio']*100:.0f}% | 買入 BTC.D>{params['buy_btc_d']} RSI<{params['buy_rsi']} | 賣出 BTC.D<{params['sell_btc_d']}")
        print(f"   ADA: {stats['total_ada']:,.0f} | ROI: {stats['roi_pct']:.1f}% | 交易: {stats['trade_count']}")
    
    # 儲存報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"ada_hybrid_optimized_{timestamp}.txt"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("ADA 混合策略優化結果\n")
        f.write("="*70 + "\n\n")
        
        f.write("最佳參數：\n")
        for key, value in best_params.items():
            f.write(f"  {key}: {value}\n")
        
        f.write(f"\n最佳績效：\n")
        f.write(f"  總 ADA：{best_stats['total_ada']:,.0f}\n")
        f.write(f"  ROI：{best_stats['roi_pct']:.1f}%\n")
        f.write(f"  質押收益：{best_stats['staking_rewards']:.2f} ADA\n")
        
        f.write(f"\nTop 3 配置：\n")
        for idx, result in enumerate(top_3, 1):
            params = result['params']
            stats = result['stats']
            f.write(f"\n{idx}. 固定{params['fixed_ratio']*100:.0f}% | ADA {stats['total_ada']:,.0f} | ROI {stats['roi_pct']:.1f}%\n")
    
    print(f"\n📄 報告已儲存：{report_file}")
    
    return best_result


if __name__ == "__main__":
    try:
        best = optimize_parameters()
    except Exception as e:
        print(f"❌ 錯誤：{e}")
        import traceback
        traceback.print_exc()
