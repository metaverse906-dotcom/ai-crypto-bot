#!/usr/bin/env python3
# tools/final_system_backtest.py
"""
最終系統完整回測
使用所有優化後的參數配置
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
import os
from datetime import datetime

DATA_DIR = 'data/backtest'
SYMBOL = 'BTC/USDT'
INITIAL_CAPITAL = 1000.0

def load_data(timeframe):
    filename = f"{DATA_DIR}/{SYMBOL.replace('/', '_')}_{timeframe}_2023-2024.csv"
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    return None

# ==================== Silver Bullet 策略 ====================
def simulate_silver_bullet(df):
    """
    最終優化版 Silver Bullet
    - 盈虧比 1:2.5
    - EMA 200
    - 時段限制
    """
    df['ema_200'] = ta.ema(df['close'], length=200)
    
    trades = []
    equity = INITIAL_CAPITAL
    
    for i in range(210, len(df), 4):  # 每4根15m = 1小時
        current = df.iloc[i]
        prev_4h = df.iloc[i-4:i]
        
        if pd.isna(current.get('ema_200')):
            continue
        
        # 時段限制
        hour = current['timestamp'].hour
        if not ((2 <= hour < 5) or (10 <= hour < 11)):
            continue
        
        signal = None
        sl = 0
        
        # 掃蕩形態
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
            
            # 盈虧比 1:2.5
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

# ==================== Hybrid SFP 策略 ====================
def simulate_hybrid_sfp(df):
    """
    最終優化版 Hybrid SFP
    - ADX > 30 (SFP)
    - RSI 60/40
    - 盈虧比 1:2.5
    - ADX > 25 (Trend)
    """
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
    
    bb = ta.bbands(df['close'], length=20, std=2.0)
    if bb is not None:
        cols = bb.columns
        df['bb_upper'] = bb[cols[cols.str.startswith('BBU')][0]]
        df['bb_lower'] = bb[cols[cols.str.startswith('BBL')][0]]
        df['bw'] = bb[cols[cols.str.startswith('BBB')][0]]
    
    df['swing_high'] = df['high'].rolling(window=50).max().shift(1)
    df['swing_low'] = df['low'].rolling(window=50).min().shift(1)
    
    trades = []
    equity = INITIAL_CAPITAL
    
    for i in range(250, len(df), 16):  # 每16根15m = 4h
        prev = df.iloc[i-1]
        
        if pd.isna(prev.get('adx')) or pd.isna(prev.get('rsi')):
            continue
        
        signal = None
        sl = 0
        setup = None
        
        # SFP（ADX > 30, RSI 60/40）
        if prev['adx'] > 30:
            if prev['high'] > prev['swing_high'] and prev['close'] < prev['swing_high']:
                if prev['rsi'] > 60:
                    signal = 'SHORT'
                    sl = prev['high']
                    setup = 'SFP'
            
            elif prev['low'] < prev['swing_low'] and prev['close'] > prev['swing_low']:
                if prev['rsi'] < 40:
                    signal = 'LONG'
                    sl = prev['low']
                    setup = 'SFP'
        
        # Trend Breakout（ADX > 25）
        if signal is None and pd.notna(prev.get('bb_upper')):
            if prev['adx'] > 25:
                bw_min = 5.0
                
                if prev['close'] > prev['bb_upper'] and prev['close'] > prev['ema_200'] and prev['bw'] > bw_min:
                    signal = 'LONG'
                    sl = prev['close'] - (2 * prev['atr'])
                    setup = 'Trend'
                
                elif prev['close'] < prev['bb_lower'] and prev['close'] < prev['ema_200'] and prev['bw'] > bw_min:
                    signal = 'SHORT'
                    sl = prev['close'] + (2 * prev['atr'])
                    setup = 'Trend'
        
        if signal:
            risk_amt = equity * 0.02
            risk_dist = abs(prev['close'] - sl)
            
            if risk_dist == 0:
                continue
            
            # 盈虧比 1:2.5
            tp = prev['close'] + (risk_dist * 2.5) if signal == 'LONG' else prev['close'] - (risk_dist * 2.5)
            
            metrics = {'pnl': 0, 'result': 'OPEN', 'setup': setup}
            
            future = df.iloc[i:i+400]
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

# ==================== 統計計算 ====================
def calculate_stats(trades, equity, strategy_name):
    if not trades:
        return None
    
    df = pd.DataFrame(trades)
    total_trades = len(trades)
    wins = len(df[df['result'] == 'WIN'])
    losses = total_trades - wins
    win_rate = (wins / total_trades) * 100
    total_return = ((equity - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    # Sharpe Ratio
    returns = [t['pnl'] / INITIAL_CAPITAL for t in trades]
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(365) if np.std(returns) > 0 else 0
    
    # 期望值
    avg_win = df[df['result'] == 'WIN']['pnl'].mean() if wins > 0 else 0
    avg_loss = df[df['result'] == 'LOSS']['pnl'].mean() if losses > 0 else 0
    expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)
    
    return {
        'strategy': strategy_name,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_return': total_return,
        'final_equity': equity,
        'sharpe_ratio': sharpe,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy
    }

# ==================== 主程序 ====================
def main():
    print("=" * 70)
    print("最終系統完整回測 (2023-2024)")
    print("使用所有優化後的參數配置")
    print("=" * 70)
    
    df = load_data('15m')
    if df is None:
        print("❌ 無法載入數據")
        return
    
    print(f"\n📊 數據範圍: {df['timestamp'].iloc[0]} - {df['timestamp'].iloc[-1]}")
    print(f"📊 總 K 線數: {len(df)}\n")
    
    # 執行回測
    results = []
    
    print("🔄 執行 Silver Bullet 回測...")
    sb_result = simulate_silver_bullet(df)
    if sb_result:
        results.append(sb_result)
    
    print("🔄 執行 Hybrid SFP 回測...")
    hs_result = simulate_hybrid_sfp(df)
    if hs_result:
        results.append(hs_result)
    
    # 輸出結果
    print("\n" + "=" * 70)
    print("📊 回測結果")
    print("=" * 70)
    
    for r in results:
        print(f"\n策略: {r['strategy']}")
        print(f"  總交易: {r['total_trades']}")
        print(f"  勝: {r['wins']} / 敗: {r['losses']}")
        print(f"  勝率: {r['win_rate']:.2f}%")
        print(f"  總回報: {r['total_return']:+.2f}%")
        print(f"  最終權益: ${r['final_equity']:.2f}")
        print(f"  Sharpe: {r['sharpe_ratio']:.2f}")
        print(f"  平均盈: ${r['avg_win']:.2f}")
        print(f"  平均虧: ${r['avg_loss']:.2f}")
        print(f"  期望值: ${r['expectancy']:.2f}")
    
    # 保存報告
    report_path = f"{DATA_DIR}/final_system_backtest.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("最終系統完整回測報告 (2023-2024)\n")
        f.write("=" * 70 + "\n\n")
        f.write("配置摘要:\n")
        f.write("- Silver Bullet: 盈虧比 1:2.5, EMA 200, 時段限制\n")
        f.write("- Hybrid SFP: ADX > 30, RSI 60/40, 盈虧比 1:2.5\n\n")
        
        for r in results:
            f.write(f"\n{r['strategy']}:\n")
            f.write(f"  總交易: {r['total_trades']}\n")
            f.write(f"  勝率: {r['win_rate']:.2f}%\n")
            f.write(f"  總回報: {r['total_return']:+.2f}%\n")
            f.write(f"  Sharpe: {r['sharpe_ratio']:.2f}\n")
            f.write(f"  期望值: ${r['expectancy']:.2f}\n")
    
    print(f"\n📄 報告已儲存: {report_path}")
    print("\n" + "=" * 70)
    print("✅ 回測完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
