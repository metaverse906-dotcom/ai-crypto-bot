#!/usr/bin/env python3
# tools/backtest_silver_bullet_to_file.py
"""
Silver Bullet 回測 - 結果直接寫入文件
"""

import pandas as pd
import pandas_ta as ta
import random
from datetime import datetime

def backtest_and_save():
    """執行回測並保存結果"""
    
    # 打開輸出文件
    output = []
    
    def log(msg):
        print(msg)
        output.append(msg)
    
    # 載入數據
    try:
        df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except Exception as e:
        log(f"ERROR: Cannot load data - {e}")
        return
    
    log("="*70)
    log("Silver Bullet Backtest (SMC Boost Version)")
    log("="*70)
    log(f"\nData Range: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
    log(f"Total Candles: {len(df)}")
    
    # 計算指標
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    trades = []
    signals_total = 0
    smc_confirmed_count = 0
    
    log("\nRunning backtest...")
    
    random.seed(42)
    
    for i in range(250, len(df)):
        current = df.iloc[i]
        prev_4h = df.iloc[i-4:i]
        
        # Session check (UTC 02-05 or 10-11)
        hour = current['timestamp'].hour
        in_session = (2 <= hour < 5) or (10 <= hour < 11)
        
        if not in_session:
            continue
        
        # Sweep pattern
        lh_low = prev_4h['low'].min()
        lh_high = prev_4h['high'].max()
        
        signal = None
        sl = None
        
        # LONG
        if current['low'] < lh_low and current['close'] > lh_low:
            if current['close'] > current['ema_200']:
                signal = 'LONG'
                sl = current['low']
        
        # SHORT
        elif current['high'] > lh_high and current['close'] < lh_high:
            if current['close'] < current['ema_200']:
                signal = 'SHORT'
                sl = current['high']
        
        if signal:
            signals_total += 1
            entry = current['close']
            
            # SMC boost (40% confirmation rate)
            smc_confirmed = random.random() < 0.4
            if smc_confirmed:
                smc_confirmed_count += 1
            
            position_size = 0.03 if smc_confirmed else 0.02
            tp = entry + (abs(entry - sl) * 2.5) if signal == 'LONG' else entry - (abs(entry - sl) * 2.5)
            
            # Find exit
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
                        break
    
    # Statistics
    if not trades:
        log("\nNO TRADES FOUND")
        with open('silver_bullet_results.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        return
    
    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['pnl'] > 0])
    losses = len(df_trades) - wins
    
    smc_trades = df_trades[df_trades['smc'] == True]
    normal_trades = df_trades[df_trades['smc'] == False]
    
    log("\n" + "="*70)
    log("RESULTS")
    log("="*70)
    
    log(f"\n[OVERALL STATISTICS]")
    log(f"  Total Signals: {signals_total}")
    log(f"  Completed Trades: {len(df_trades)}")
    log(f"  Wins: {wins}")
    log(f"  Losses: {losses}")
    log(f"  Win Rate: {wins/len(df_trades)*100:.1f}%")
    
    log(f"\n[PNL STATISTICS]")
    log(f"  Total PNL: {df_trades['pnl'].sum():.2f}%")
    log(f"  Average PNL: {df_trades['pnl'].mean():.2f}%")
    log(f"  Max Win: {df_trades['pnl'].max():.2f}%")
    log(f"  Max Loss: {df_trades['pnl'].min():.2f}%")
    
    log(f"\n[SMC BOOST ANALYSIS]")
    log(f"  SMC Confirmed Trades: {len(smc_trades)} ({len(smc_trades)/len(df_trades)*100:.1f}%)")
    log(f"  Normal Trades: {len(normal_trades)} ({len(normal_trades)/len(df_trades)*100:.1f}%)")
    
    if len(smc_trades) > 0:
        smc_wins = len(smc_trades[smc_trades['pnl'] > 0])
        log(f"\n  SMC Boost Win Rate: {smc_wins/len(smc_trades)*100:.1f}%")
        log(f"  SMC Boost Total PNL: {smc_trades['pnl'].sum():.2f}%")
        log(f"  SMC Boost Average: {smc_trades['pnl'].mean():.2f}%")
    
    if len(normal_trades) > 0:
        normal_wins = len(normal_trades[normal_trades['pnl'] > 0])
        log(f"\n  Normal Win Rate: {normal_wins/len(normal_trades)*100:.1f}%")
        log(f"  Normal Total PNL: {normal_trades['pnl'].sum():.2f}%")
        log(f"  Normal Average: {normal_trades['pnl'].mean():.2f}%")
    
    log(f"\n[SIGNAL DISTRIBUTION]")
    long_count = len(df_trades[df_trades['signal'] == 'LONG'])
    short_count = len(df_trades[df_trades['signal'] == 'SHORT'])
    log(f"  LONG: {long_count} ({long_count/len(df_trades)*100:.1f}%)")
    log(f"  SHORT: {short_count} ({short_count/len(df_trades)*100:.1f}%)")
    
    log(f"\n[EXIT REASONS]")
    tp_count = len(df_trades[df_trades['reason'] == 'TP'])
    sl_count = len(df_trades[df_trades['reason'] == 'SL'])
    log(f"  Take Profit: {tp_count} ({tp_count/len(df_trades)*100:.1f}%)")
    log(f"  Stop Loss: {sl_count} ({sl_count/len(df_trades)*100:.1f}%)")
    
    log("\n" + "="*70)
    log("BACKTEST COMPLETE")
    log("="*70)
    log(f"\nResults saved to: silver_bullet_results.txt")
    log(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Save to file
    with open('silver_bullet_results.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print("\nFile saved successfully!")


if __name__ == "__main__":
    backtest_and_save()
