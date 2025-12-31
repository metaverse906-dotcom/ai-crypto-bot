#!/usr/bin/env python3
"""
快速測試改良版回測系統
使用本地數據測試 Silver Bullet 和 SFP 策略
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy import stats
import sys
sys.path.append('tools')
from robust_backtest_validator import RobustValidator

DATA_DIR = 'data/backtest'
INITIAL_CAPITAL = 1000.0

def load_data():
    """載入本地數據"""
    df = pd.read_csv(f'{DATA_DIR}/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def backtest_silver_bullet(df):
    """Silver Bullet 回測"""
    df['ema_200'] = ta.ema(df['close'], length=200)
    
    trades = []
    equity = INITIAL_CAPITAL
    
    for i in range(210, len(df), 4):
        current = df.iloc[i]
        prev_4h = df.iloc[i-4:i]
        
        if pd.isna(current.get('ema_200')):
            continue
        
        hour = current['timestamp'].hour
        if not ((2 <= hour < 5) or (10 <= hour < 11)):
            continue
        
        signal = None
        sl = 0
        
        lh_low = prev_4h['low'].min()
        if current['low'] < lh_low and current['close'] > lh_low:
            if current['close'] > current['ema_200']:
                signal = 'LONG'
                sl = current['low']
        
        lh_high = prev_4h['high'].max()
        if current['high'] > lh_high and current['close'] < lh_high:
            if current['close'] < current['ema_200']:
                signal = 'SHORT'
                sl = current['high']
        
        if signal:
            risk_amt = equity * 0.02
            risk_dist = abs(current['close'] - sl)
            
            if risk_dist == 0:
                continue
            
            tp = current['close'] + (risk_dist * 2.5) if signal == 'LONG' else current['close'] - (risk_dist * 2.5)
            
            metrics = {'pnl': 0, 'result': 'OPEN'}
            
            future = df.iloc[i+1:i+100]
            for _, candle in future.iterrows():
                if signal == 'LONG':
                    if candle['low'] <= sl:
                        metrics['pnl'] = -risk_amt
                        metrics['result'] = 'LOSS'
                        break
                    if candle['high'] >= tp:
                        metrics['pnl'] = risk_amt * 2.5
                        metrics['result'] = 'WIN'
                        break
                else:
                    if candle['high'] >= sl:
                        metrics['pnl'] = -risk_amt
                        metrics['result'] = 'LOSS'
                        break
                    if candle['low'] <= tp:
                        metrics['pnl'] = risk_amt * 2.5
                        metrics['result'] = 'WIN'
                        break
            
            if metrics['result'] != 'OPEN':
                equity += metrics['pnl']
                trades.append(metrics)
    
    return calculate_stats(trades, equity, 'Silver Bullet')

def backtest_hybrid_sfp(df):
    """Hybrid SFP 回測"""
    # 從15m聚合到4h
    df = df.set_index('timestamp')
    df_4h = df.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    
    df_4h['ema_200'] = ta.ema(df_4h['close'], length=200)
    df_4h['rsi'] = ta.rsi(df_4h['close'], length=14)
    df_4h['atr'] = ta.atr(df_4h['high'], df_4h['low'], df_4h['close'], length=14)
    df_4h['adx'] = ta.adx(df_4h['high'], df_4h['low'], df_4h['close'], length=14)['ADX_14']
    
    bb = ta.bbands(df_4h['close'], length=20, std=2.0)
    if bb is not None:
        cols = bb.columns
        df_4h['bb_upper'] = bb[cols[cols.str.startswith('BBU')][0]]
        df_4h['bb_lower'] = bb[cols[cols.str.startswith('BBL')][0]]
        df_4h['bw'] = bb[cols[cols.str.startswith('BBB')][0]]
    
    df_4h['swing_high'] = df_4h['high'].rolling(window=50).max().shift(1)
    df_4h['swing_low'] = df_4h['low'].rolling(window=50).min().shift(1)
    
    trades = []
    equity = INITIAL_CAPITAL
    
    for i in range(250, len(df_4h)):
        prev = df_4h.iloc[i-1]
        
        if pd.isna(prev.get('adx')) or pd.isna(prev.get('rsi')):
            continue
        
        signal = None
        sl = 0
        
        # SFP
        if prev['adx'] > 30:
            if prev['high'] > prev['swing_high'] and prev['close'] < prev['swing_high']:
                if prev['rsi'] > 60:
                    signal = 'SHORT'
                    sl = prev['high']
            elif prev['low'] < prev['swing_low'] and prev['close'] > prev['swing_low']:
                if prev['rsi'] < 40:
                    signal = 'LONG'
                    sl = prev['low']
        
        # Trend
        if signal is None and pd.notna(prev.get('bb_upper')):
            if prev['adx'] > 25:
                if prev['close'] > prev['bb_upper'] and prev['close'] > prev['ema_200'] and prev['bw'] > 5.0:
                    signal = 'LONG'
                    sl = prev['close'] - (2 * prev['atr'])
                elif prev['close'] < prev['bb_lower'] and prev['close'] < prev['ema_200'] and prev['bw'] > 5.0:
                    signal = 'SHORT'
                    sl = prev['close'] + (2 * prev['atr'])
        
        if signal:
            risk_amt = equity * 0.02
            risk_dist = abs(prev['close'] - sl)
            
            if risk_dist == 0:
                continue
            
            tp = prev['close'] + (risk_dist * 2.5) if signal == 'LONG' else prev['close'] - (risk_dist * 2.5)
            
            metrics = {'pnl': 0, 'result': 'OPEN'}
            
            future = df_4h.iloc[i:i+100]
            for _, candle in future.iterrows():
                if signal == 'LONG':
                    if candle['low'] <= sl:
                        metrics['pnl'] = -risk_amt
                        metrics['result'] = 'LOSS'
                        break
                    if candle['high'] >= tp:
                        metrics['pnl'] = risk_amt * 2.5
                        metrics['result'] = 'WIN'
                        break
                else:
                    if candle['high'] >= sl:
                        metrics['pnl'] = -risk_amt
                        metrics['result'] = 'LOSS'
                        break
                    if candle['low'] <= tp:
                        metrics['pnl'] = risk_amt * 2.5
                        metrics['result'] = 'WIN'
                        break
            
            if metrics['result'] != 'OPEN':
                equity += metrics['pnl']
                trades.append(metrics)
    
    return calculate_stats(trades, equity, 'Hybrid SFP')

def calculate_stats(trades, equity, strategy_name):
    """計算統計指標"""
    if not trades:
        return None
    
    df = pd.DataFrame(trades)
    total_trades = len(trades)
    wins = len(df[df['result'] == 'WIN'])
    win_rate = (wins / total_trades) * 100
    total_return = ((equity - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    returns = [t['pnl'] / INITIAL_CAPITAL for t in trades]
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(365) if np.std(returns) > 0 else 0
    
    return {
        'strategy': strategy_name,
        'total_trades': total_trades,
        'wins': wins,
        'win_rate': win_rate,
        'total_return': total_return,
        'final_equity': equity,
        'sharpe': sharpe,
        'trade_returns': [t['pnl'] / INITIAL_CAPITAL * 100 for t in trades]
    }

def main():
    # 設置輸出文件
    output_file = 'backtest_results_detailed.txt'
    import sys
    
    # 同時輸出到終端和文件
    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()
    
    f = open(output_file, 'w', encoding='utf-8')
    original_stdout = sys.stdout
    sys.stdout = Tee(sys.stdout, f)
    
    try:
        print("=" * 70)
        print("🧪 測試改良版回測系統 (2023-2024 BTC/USDT)")
        print("=" * 70)
        
        df = load_data()
        print(f"\n📊 數據範圍: {df['timestamp'].iloc[0]} - {df['timestamp'].iloc[-1]}")
        print(f"📊 總 K 線數: {len(df)}\n")
        
        # Silver Bullet
        print("🔄 執行 Silver Bullet 回測...")
        sb_result = backtest_silver_bullet(df.copy())
        
        # Hybrid SFP
        print("🔄 執行 Hybrid SFP 回測...")
        sfp_result = backtest_hybrid_sfp(df.copy())
        
        # 顯示結果
        for result in [sb_result, sfp_result]:
            if not result:
                continue
            
            print("\n" + "=" * 70)
            print(f"📊 {result['strategy']} 回測結果")
            print("=" * 70)
            print(f"總交易: {result['total_trades']}")
            print(f"勝率: {result['win_rate']:.2f}%")
            print(f"總回報: {result['total_return']:+.2f}%")
            print(f"最終權益: ${result['final_equity']:.2f}")
            print(f"Sharpe: {result['sharpe']:.2f}")
            
            # 穩健驗證
            print("\n" + "-" * 70)
            print("🔒 穩健性驗證")
            print("-" * 70)
            
            validator = RobustValidator(n_bootstrap=1000, trim_percent=0.05)
            robust_results = validator.validate(result['trade_returns'])
            
            bs = robust_results['bootstrap_ci']
            tm = robust_results['trimmed_stats']
            wc = robust_results['worst_case']
            
            print(f"\nBootstrap 95% CI: [{bs['ci_lower']:.2f}%, {bs['ci_upper']:.2f}%]")
            print(f"Trimmed Mean (去除前後5%): {tm['trimmed_mean']:.2f}%")
            print(f"極端值影響: {tm['impact_percent']:+.2f}%")
            print(f"最差 10% 平均: {wc['worst_10_mean']:.2f}%")
            print(f"最大連續虧損: {wc['max_consecutive_losses']} 次")
            print(f"\n穩健性評分: {robust_results['robustness_score']:.1f}/100")
            print(f"評級: {robust_results['rating']}")
            
            # 判斷穩健性
            if tm['trimmed_mean'] > 0:
                print("✅ 策略穩健（去除極端值後仍盈利）")
            else:
                print("⚠️ 策略可能依賴極端值")
        
        print("\n" + "=" * 70)
        print("✅ 測試完成")
        print(f"📄 詳細結果已保存至: {output_file}")
        print("=" * 70)
    
    finally:
        sys.stdout = original_stdout
        f.close()

if __name__ == "__main__":
    main()
