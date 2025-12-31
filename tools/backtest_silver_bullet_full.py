#!/usr/bin/env python3
# tools/backtest_silver_bullet_full.py
"""
Silver Bullet 完整回測（SMC 加碼版）
"""

import pandas as pd
import pandas_ta as ta
import random

def backtest_silver_bullet():
    """Silver Bullet 完整回測"""
    
    # 載入數據
    try:
        df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except:
        print("❌ 找不到數據文件")
        return
    
    print("="*70)
    print("🎯 Silver Bullet 策略回測（SMC 加碼版）")
    print("="*70)
    print(f"\n數據範圍: {df.iloc[0]['timestamp']} 到 {df.iloc[-1]['timestamp']}")
    print(f"總K線數: {len(df)}")
    
    # 計算指標
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    trades = []
    signals_total = 0
    smc_confirmed_count = 0
    
    print("\n開始回測...\n")
    
    for i in range(250, len(df)):
        current = df.iloc[i]
        prev_4h = df.iloc[i-4:i]
        
        # 時段檢查（UTC 02-05 或 10-11）
        hour = current['timestamp'].hour
        in_session = (2 <= hour < 5) or (10 <= hour < 11)
        
        if not in_session:
            continue
        
        # 掃蕩形態
        lh_low = prev_4h['low'].min()
        lh_high = prev_4h['high'].max()
        
        signal = None
        sl = None
        
        # LONG 信號
        if current['low'] < lh_low and current['close'] > lh_low:
            if current['close'] > current['ema_200']:
                signal = 'LONG'
                sl = current['low']
        
        # SHORT 信號
        elif current['high'] > lh_high and current['close'] < lh_high:
            if current['close'] < current['ema_200']:
                signal = 'SHORT'
                sl = current['high']
        
        if signal:
            signals_total += 1
            entry = current['close']
            
            # SMC 加碼模擬（假設 40% 確認率）
            smc_confirmed = random.random() < 0.4
            if smc_confirmed:
                smc_confirmed_count += 1
            
            position_size = 0.03 if smc_confirmed else 0.02  # 3% vs 2%
            
            tp = entry + (abs(entry - sl) * 2.5) if signal == 'LONG' else entry - (abs(entry - sl) * 2.5)
            
            # 找出場點
            exit_found = False
            for j in range(i+1, min(i+100, len(df))):
                candle = df.iloc[j]
                
                if signal == 'LONG':
                    if candle['low'] <= sl:
                        pnl = ((sl - entry) / entry) * position_size * 100
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': sl,
                            'pnl': pnl,
                            'reason': 'SL',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        exit_found = True
                        break
                    elif candle['high'] >= tp:
                        pnl = ((tp - entry) / entry) * position_size * 100
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': tp,
                            'pnl': pnl,
                            'reason': 'TP',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        exit_found = True
                        break
                else:  # SHORT
                    if candle['high'] >= sl:
                        pnl = ((entry - sl) / entry) * position_size * 100
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': sl,
                            'pnl': pnl,
                            'reason': 'SL',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        exit_found = True
                        break
                    elif candle['low'] <= tp:
                        pnl = ((entry - tp) / entry) * position_size * 100
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': tp,
                            'pnl': pnl,
                            'reason': 'TP',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        exit_found = True
                        break
    
    # 統計結果
    if not trades:
        print("❌ 無交易紀錄")
        return
    
    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['pnl'] > 0])
    losses = len(df_trades) - wins
    
    # SMC 加碼交易分析
    smc_trades = df_trades[df_trades['smc'] == True]
    normal_trades = df_trades[df_trades['smc'] == False]
    
    print("="*70)
    print("📊 回測結果")
    print("="*70)
    
    print(f"\n【整體統計】")
    print(f"  總信號數: {signals_total}")
    print(f"  完成交易: {len(df_trades)}")
    print(f"  獲利筆數: {wins}")
    print(f"  虧損筆數: {losses}")
    print(f"  勝率: {wins/len(df_trades)*100:.1f}%")
    
    print(f"\n【盈虧統計】")
    print(f"  總盈虧: {df_trades['pnl'].sum():.2f}%")
    print(f"  平均盈虧: {df_trades['pnl'].mean():.2f}%")
    print(f"  最大獲利: {df_trades['pnl'].max():.2f}%")
    print(f"  最大虧損: {df_trades['pnl'].min():.2f}%")
    
    print(f"\n【SMC 加碼分析】")
    print(f"  SMC 確認交易: {len(smc_trades)} ({len(smc_trades)/len(df_trades)*100:.1f}%)")
    print(f"  一般交易: {len(normal_trades)} ({len(normal_trades)/len(df_trades)*100:.1f}%)")
    
    if len(smc_trades) > 0:
        smc_wins = len(smc_trades[smc_trades['pnl'] > 0])
        print(f"\n  SMC 加碼交易勝率: {smc_wins/len(smc_trades)*100:.1f}%")
        print(f"  SMC 加碼總盈虧: {smc_trades['pnl'].sum():.2f}%")
        print(f"  SMC 加碼平均: {smc_trades['pnl'].mean():.2f}%")
    
    if len(normal_trades) > 0:
        normal_wins = len(normal_trades[normal_trades['pnl'] > 0])
        print(f"\n  一般交易勝率: {normal_wins/len(normal_trades)*100:.1f}%")
        print(f"  一般交易總盈虧: {normal_trades['pnl'].sum():.2f}%")
        print(f"  一般交易平均: {normal_trades['pnl'].mean():.2f}%")
    
    print(f"\n【信號分布】")
    long_count = len(df_trades[df_trades['signal'] == 'LONG'])
    short_count = len(df_trades[df_trades['signal'] == 'SHORT'])
    print(f"  LONG: {long_count} ({long_count/len(df_trades)*100:.1f}%)")
    print(f"  SHORT: {short_count} ({short_count/len(df_trades)*100:.1f}%)")
    
    print(f"\n【出場原因】")
    tp_count = len(df_trades[df_trades['reason'] == 'TP'])
    sl_count = len(df_trades[df_trades['reason'] == 'SL'])
    print(f"  止盈: {tp_count} ({tp_count/len(df_trades)*100:.1f}%)")
    print(f"  止損: {sl_count} ({sl_count/len(df_trades)*100:.1f}%)")
    
    print("\n" + "="*70)
    print("✅ 回測完成")
    print("="*70)


if __name__ == "__main__":
    random.seed(42)  # 固定隨機種子以確保可重現
    backtest_silver_bullet()
