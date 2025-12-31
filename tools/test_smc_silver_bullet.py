#!/usr/bin/env python3
# tools/test_smc_silver_bullet.py
"""
測試 SMC 強化版 Silver Bullet 策略
對比原版與 SMC 版本的穩健性
"""

import sys
import os
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# 修正導入路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.robust_backtest_validator import RobustValidator
from tools.smc_detector import SMCDetector

# ==================== 模擬簡化版策略 ====================

def simulate_silver_bullet_original(df):
    """
    原版 Silver Bullet（無 SMC 過濾）
    """
    df['ema_200'] = ta.ema(df['close'], length=200)
    
    trades = []
    
    for i in range(210, len(df)):
        # 掃蕩形態偵測
        last_hour = df.iloc[i-5:i]
        current = df.iloc[i]
        
        if pd.isna(current['ema_200']):
            continue
        
        signal = None
        sl = 0
        
        # SHORT 信號
        if current['high'] > last_hour['high'].max() and current['close'] < last_hour['high'].max():
            if current['close'] < current['ema_200']:
                signal = 'SHORT'
                sl = current['high']
        
        # LONG 信號
        elif current['low'] < last_hour['low'].min() and current['close'] > last_hour['low'].min():
            if current['close'] > current['ema_200']:
                signal = 'LONG'
                sl = current['low']
        
        if signal:
            entry = current['close']
            dist = abs(entry - sl)
            tp = entry - dist * 2.5 if signal == 'SHORT' else entry + dist * 2.5
            
            trades.append({
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'signal': signal,
                'entry_time': current['timestamp']
            })
    
    return trades


def simulate_silver_bullet_smc(df):
    """
    SMC 強化版 Silver Bullet
    """
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # 初始化 SMC 偵測器
    smc = SMCDetector()
    smc.scan(df)
    
    trades = []
    
    for i in range(210, len(df)):
        last_hour = df.iloc[i-5:i]
        current = df.iloc[i]
        
        if pd.isna(current['ema_200']):
            continue
        
        signal = None
        sl = 0
        
        # SHORT 信號
        if current['high'] > last_hour['high'].max() and current['close'] < last_hour['high'].max():
            if current['close'] < current['ema_200']:
                signal = 'SHORT'
                sl = current['high']
        
        # LONG 信號
        elif current['low'] < last_hour['low'].min() and current['close'] > last_hour['low'].min():
            if current['close'] > current['ema_200']:
                signal = 'LONG'
                sl = current['low']
        
        if signal:
            # SMC 過濾
            if not smc.check_ob_confluence(current['close'], signal):
                continue  # 跳過無 OB 支持的信號
            
            entry = current['close']
            dist = abs(entry - sl)
            tp = entry - dist * 2.5 if signal == 'SHORT' else entry + dist * 2.5
            
            trades.append({
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'signal': signal,
                'entry_time': current['timestamp']
            })
    
    return trades


def calculate_returns(df, trades):
    """
    計算交易回報率
    """
    returns = []
    
    for trade in trades:
        entry = trade['entry']
        sl = trade['sl']
        tp = trade['tp']
        signal = trade['signal']
        
        # 找到後續價格走勢
        entry_idx = df[df['timestamp'] == trade['entry_time']].index[0]
        future = df.iloc[entry_idx+1:entry_idx+50]
        
        if len(future) == 0:
            continue
        
        # 檢查是否觸發 SL 或 TP
        for j, row in future.iterrows():
            if signal == 'LONG':
                if row['low'] <= sl:  # 觸發止損
                    ret = (sl - entry) / entry * 100
                    returns.append(ret)
                    break
                elif row['high'] >= tp:  # 觸發止盈
                    ret = (tp - entry) / entry * 100
                    returns.append(ret)
                    break
            else:  # SHORT
                if row['high'] >= sl:
                    ret = (entry - sl) / entry * 100
                    returns.append(ret)
                    break
                elif row['low'] <= tp:
                    ret = (entry - tp) / entry * 100
                    returns.append(ret)
                    break
    
    return returns


# ==================== 主測試 ====================

def main():
    import sys
    
    # 重定向輸出到文件
    output_file = 'smc_comparison_results.txt'
    sys.stdout = open(output_file, 'w', encoding='utf-8')
    
    print("=" * 70)
    print("🧪 SMC 強化版 Silver Bullet 策略驗證")
    print("=" * 70)
    
    # 載入數據
    print("\n📊 載入 2023-2024 BTC/USDT 15m 數據...")
    df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"   數據範圍: {df['timestamp'].min()} - {df['timestamp'].max()}")
    print(f"   總 K 線數: {len(df)}")
    
    # 測試原版
    print("\n" + "=" * 70)
    print("🔄 執行原版 Silver Bullet 回測")
    print("=" * 70)
    trades_original = simulate_silver_bullet_original(df.copy())
    print(f"   發現信號: {len(trades_original)} 個")
    
    returns_original = calculate_returns(df, trades_original)
    print(f"   完成交易: {len(returns_original)} 筆")
    
    if returns_original:
        avg_return = sum(returns_original) / len(returns_original)
        print(f"   平均回報: {avg_return:.2f}%")
        wins = len([r for r in returns_original if r > 0])
        print(f"   勝率: {wins / len(returns_original) * 100:.1f}%")
    
    # 測試 SMC 版
    print("\n" + "=" * 70)
    print("🔄 執行 SMC 強化版 Silver Bullet 回測")
    print("=" * 70)
    trades_smc = simulate_silver_bullet_smc(df.copy())
    print(f"   發現信號: {len(trades_smc)} 個")
    
    returns_smc = calculate_returns(df, trades_smc)
    print(f"   完成交易: {len(returns_smc)} 筆")
    
    if returns_smc:
        avg_return = sum(returns_smc) / len(returns_smc)
        print(f"   平均回報: {avg_return:.2f}%")
        wins = len([r for r in returns_smc if r > 0])
        print(f"   勝率: {wins / len(returns_smc) * 100:.1f}%")
    
    # 穩健性驗證
    validator = RobustValidator()
    
    print("\n" + "=" * 70)
    print("📊 原版 Silver Bullet 穩健性驗證")
    print("=" * 70)
    
    if returns_original and len(returns_original) >= 30:
        results_original = validator.validate(returns_original)
        print(validator.generate_report(results_original, "Silver Bullet (原版)"))
    else:
        print("❌ 交易數量不足（需要至少 30 筆）")
    
    print("\n" + "=" * 70)
    print("📊 SMC 強化版 Silver Bullet 穩健性驗證")
    print("=" * 70)
    
    if returns_smc and len(returns_smc) >= 30:
        results_smc = validator.validate(returns_smc)
        print(validator.generate_report(results_smc, "Silver Bullet (SMC版)"))
    else:
        print("❌ 交易數量不足（需要至少 30 筆）")
    
    # 對比總結
    if returns_original and returns_smc and len(returns_original) >= 30 and len(returns_smc) >= 30:
        print("\n" + "=" * 70)
        print("🔍 對比總結")
        print("=" * 70)
        
        print(f"\n📊 信號數量:")
        print(f"   原版: {len(returns_original)} 筆")
        print(f"   SMC版: {len(returns_smc)} 筆")
        filter_rate = (1 - len(returns_smc)/len(returns_original)) * 100 if len(returns_original) > 0 else 0
        print(f"   過濾率: {filter_rate:.1f}% (SMC 過濾掉 {filter_rate:.1f}% 的信號)")
        
        print(f"\n📈 穩健性指標對比:")
        
        print(f"\n   Trimmed Mean (去除前後5%):")
        orig_tm = results_original['trimmed_mean']['mean']
        smc_tm = results_smc['trimmed_mean']['mean']
        print(f"      原版: {orig_tm:.2f}%")
        print(f"      SMC版: {smc_tm:.2f}%")
        improvement_tm = smc_tm - orig_tm
        print(f"      改善: {improvement_tm:+.2f}% {'✅' if improvement_tm > 0 else '❌'}")
        
        print(f"\n   極端值影響:")
        orig_ei = results_original['trimmed_mean']['extreme_impact']
        smc_ei = results_smc['trimmed_mean']['extreme_impact']
        print(f"      原版: {orig_ei:.2f}%")
        print(f"      SMC版: {smc_ei:.2f}%")
        reduction = orig_ei - smc_ei
        print(f"      降低: {reduction:.2f}% {'✅' if reduction > 0 else '❌'}")
        
        print(f"\n   穩健性評分:")
        orig_score = results_original['robustness_score']['score']
        smc_score = results_smc['robustness_score']['score']
        orig_rating = results_original['robustness_score']['rating']
        smc_rating = results_smc['robustness_score']['rating']
        print(f"      原版: {orig_score:.0f}/100 ({orig_rating})")
        print(f"      SMC版: {smc_score:.0f}/100 ({smc_rating})")
        score_gain = smc_score - orig_score
        print(f"      提升: {score_gain:+.0f} 分 {'✅' if score_gain > 0 else '❌'}")
        
        print(f"\n   最差 10% 平均:")
        orig_worst = results_original['worst_case']['worst_10_pct_avg']
        smc_worst = results_smc['worst_case']['worst_10_pct_avg']
        print(f"      原版: {orig_worst:.2f}%")
        print(f"      SMC版: {smc_worst:.2f}%")
        print(f"      改善: {smc_worst - orig_worst:+.2f}% {'✅' if smc_worst > orig_worst else '❌'}")
        
        print("\n" + "=" * 70)
        print("✅ 驗證完成")
        print("=" * 70)
        print(f"\n結果已保存到: {output_file}")
    
    sys.stdout.close()


if __name__ == "__main__":
    main()
    
    # 同時輸出到控制台
    with open('smc_comparison_results.txt', 'r', encoding='utf-8') as f:
        print(f.read())
