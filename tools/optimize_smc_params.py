#!/usr/bin/env python3
# tools/optimize_smc_params.py
"""
SMC 參數優化分析
測試不同的 atr_multiplier 和 lookback 組合
找出最佳平衡點
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


def simulate_silver_bullet_original(df):
    """原版 Silver Bullet"""
    df['ema_200'] = ta.ema(df['close'], length=200)
    
    trades = []
    
    for i in range(210, len(df)):
        last_hour = df.iloc[i-5:i]
        current = df.iloc[i]
        
        if pd.isna(current['ema_200']):
            continue
        
        signal = None
        sl = 0
        
        if current['high'] > last_hour['high'].max() and current['close'] < last_hour['high'].max():
            if current['close'] < current['ema_200']:
                signal = 'SHORT'
                sl = current['high']
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


def simulate_silver_bullet_smc(df, atr_mult, lookback):
    """SMC 強化版 Silver Bullet（可調參數）"""
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # 使用指定參數初始化 SMC
    smc = SMCDetector(atr_multiplier=atr_mult, lookback=lookback)
    smc.scan(df)
    
    trades = []
    
    for i in range(210, len(df)):
        last_hour = df.iloc[i-5:i]
        current = df.iloc[i]
        
        if pd.isna(current['ema_200']):
            continue
        
        signal = None
        sl = 0
        
        if current['high'] > last_hour['high'].max() and current['close'] < last_hour['high'].max():
            if current['close'] < current['ema_200']:
                signal = 'SHORT'
                sl = current['high']
        elif current['low'] < last_hour['low'].min() and current['close'] > last_hour['low'].min():
            if current['close'] > current['ema_200']:
                signal = 'LONG'
                sl = current['low']
        
        if signal:
            # SMC 過濾
            if not smc.check_ob_confluence(current['close'], signal):
                continue
            
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
    """計算交易回報率"""
    returns = []
    
    for trade in trades:
        entry = trade['entry']
        sl = trade['sl']
        tp = trade['tp']
        signal = trade['signal']
        
        entry_idx = df[df['timestamp'] == trade['entry_time']].index[0]
        future = df.iloc[entry_idx+1:entry_idx+50]
        
        if len(future) == 0:
            continue
        
        for j, row in future.iterrows():
            if signal == 'LONG':
                if row['low'] <= sl:
                    ret = (sl - entry) / entry * 100
                    returns.append(ret)
                    break
                elif row['high'] >= tp:
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


def evaluate_params(df, atr_mult, lookback):
    """評估特定參數組合"""
    try:
        trades = simulate_silver_bullet_smc(df.copy(), atr_mult, lookback)
        returns = calculate_returns(df, trades)
        
        if len(returns) < 30:
            return None
        
        validator = RobustValidator()
        results = validator.validate(returns)
        
        # 檢查是否有錯誤
        if 'error' in results:
            return None
        
        return {
            'atr_mult': atr_mult,
            'lookback': lookback,
            'signal_count': len(returns),
            'avg_return': sum(returns) / len(returns),
            'win_rate': len([r for r in returns if r > 0]) / len(returns) * 100,
            'trimmed_mean': results.get('trimmed_mean', {}).get('mean', 0),
            'extreme_impact': results.get('trimmed_mean', {}).get('extreme_impact', 0),
            'robustness_score': results.get('robustness_score', {}).get('score', 0),
            'worst_10_avg': results.get('worst_case', {}).get('worst_10_pct_avg', 0),
            'max_drawdown': results.get('worst_case', {}).get('max_consecutive_losses', 0)
        }
    except Exception as e:
        print(f"錯誤: {e}")
        return None


def main():
    print("=" * 70)
    print("🔍 SMC 參數優化分析")
    print("=" * 70)
    
    # 載入數據
    print("\n📊 載入數據...")
    df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   總 K 線數: {len(df)}")
    
    # 測試參數範圍
    atr_multipliers = [1.0, 1.2, 1.5, 2.0]
    lookbacks = [10, 20, 30, 50]
    
    print(f"\n🧪 測試參數組合...")
    print(f"   ATR 倍數: {atr_multipliers}")
    print(f"   Lookback: {lookbacks}")
    print(f"   總組合數: {len(atr_multipliers) * len(lookbacks)}")
    
    results = []
    
    for atr_mult in atr_multipliers:
        for lookback in lookbacks:
            print(f"\n   測試 ATR={atr_mult}, Lookback={lookback}...", end=" ")
            
            result = evaluate_params(df, atr_mult, lookback)
            
            if result:
                results.append(result)
                print(f"✅ 信號: {result['signal_count']}, 評分: {result['robustness_score']:.0f}")
            else:
                print("❌ 信號不足")
    
    # 排序結果
    print("\n" + "=" * 70)
    print("📊 參數優化結果")
    print("=" * 70)
    
    if not results:
        print("❌ 無有效結果")
        return
    
    # 創建 DataFrame
    df_results = pd.DataFrame(results)
    
    # 按穩健性評分排序
    df_results = df_results.sort_values('robustness_score', ascending=False)
    
    print("\n【按穩健性評分排序】")
    print(df_results[['atr_mult', 'lookback', 'signal_count', 'trimmed_mean', 
                      'extreme_impact', 'robustness_score']].to_string(index=False))
    
    # 找出最佳參數（多目標優化）
    print("\n" + "=" * 70)
    print("🎯 最佳參數推薦")
    print("=" * 70)
    
    # 目標 1：信號量適中（800-2000）且穩健性最高
    moderate_signals = df_results[
        (df_results['signal_count'] >= 800) & 
        (df_results['signal_count'] <= 2000)
    ]
    
    if not moderate_signals.empty:
        best_moderate = moderate_signals.iloc[0]
        print(f"\n✅ 方案 1：平衡型（推薦）")
        print(f"   參數: ATR={best_moderate['atr_mult']}, Lookback={best_moderate['lookback']}")
        print(f"   信號量: {best_moderate['signal_count']:.0f} 筆")
        print(f"   Trimmed Mean: {best_moderate['trimmed_mean']:.2f}%")
        print(f"   極端值影響: {best_moderate['extreme_impact']:.2f}%")
        print(f"   穩健性評分: {best_moderate['robustness_score']:.0f}/100")
        print(f"   最差10%平均: {best_moderate['worst_10_avg']:.2f}%")
    
    # 目標 2：極端值影響最低
    best_extreme = df_results.loc[df_results['extreme_impact'].idxmin()]
    print(f"\n✅ 方案 2：最穩健型")
    print(f"   參數: ATR={best_extreme['atr_mult']}, Lookback={best_extreme['lookback']}")
    print(f"   信號量: {best_extreme['signal_count']:.0f} 筆")
    print(f"   Trimmed Mean: {best_extreme['trimmed_mean']:.2f}%")
    print(f"   極端值影響: {best_extreme['extreme_impact']:.2f}% ⭐")
    print(f"   穩健性評分: {best_extreme['robustness_score']:.0f}/100")
    
    # 目標 3：Trimmed Mean 最高
    best_tm = df_results.loc[df_results['trimmed_mean'].idxmax()]
    print(f"\n✅ 方案 3：最佳基礎收益型")
    print(f"   參數: ATR={best_tm['atr_mult']}, Lookback={best_tm['lookback']}")
    print(f"   信號量: {best_tm['signal_count']:.0f} 筆")
    print(f"   Trimmed Mean: {best_tm['trimmed_mean']:.2f}% ⭐")
    print(f"   極端值影響: {best_tm['extreme_impact']:.2f}%")
    print(f"   穩健性評分: {best_tm['robustness_score']:.0f}/100")
    
    # 保存完整結果
    output_file = 'smc_param_optimization.csv'
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n" + "=" * 70)
    print(f"✅ 完整結果已保存至: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
