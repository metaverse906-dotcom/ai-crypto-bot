#!/usr/bin/env python3
# tools/backtest_silver_bullet_fixed.py
"""
Silver Bullet 回測 - 修正盈虧計算版本
"""

import pandas as pd
import pandas_ta as ta
import random
from datetime import datetime

def backtest_and_save():
    """執行回測並保存結果"""
    
    output = []
    
    def log(msg):
        print(msg)
        output.append(msg)
    
    # 載入數據
    try:
        df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except Exception as e:
        log(f"ERROR: {e}")
        return
    
    log("="*70)
    log("Silver Bullet Backtest (FIXED PNL Calculation)")
    log("="*70)
    log(f"\nData: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
    log(f"Candles: {len(df)}")
    
    # 計算指標
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    trades = []
    random.seed(42)
    
    log("\nRunning backtest...\n")
    
    for i in range(250, len(df)):
        current = df.iloc[i]
        prev_4h = df.iloc[i-4:i]
        
        hour = current['timestamp'].hour
        in_session = (2 <= hour < 5) or (10 <= hour < 11)
        
        if not in_session:
            continue
        
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
            entry = current['close']
            
            # SMC 加碼（40% 確認率）
            smc_confirmed = random.random() < 0.4
            position_size = 0.03 if smc_confirmed else 0.02
            
            tp = entry + (abs(entry - sl) * 2.5) if signal == 'LONG' else entry - (abs(entry - sl) * 2.5)
            
            # 找出場
            for j in range(i+1, min(i+100, len(df))):
                candle = df.iloc[j]
                
                # ⭐ 修正：先計算價格變化百分比
                if signal == 'LONG':
                    if candle['low'] <= sl:
                        price_change_pct = ((sl - entry) / entry) * 100  # 價格變化 %
                        capital_impact = price_change_pct * position_size  # 對總資金影響
                        
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': sl,
                            'price_pnl': price_change_pct,  # ⭐ 交易盈虧 %
                            'capital_pnl': capital_impact,  # 對資金影響
                            'reason': 'SL',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        break
                    elif candle['high'] >= tp:
                        price_change_pct = ((tp - entry) / entry) * 100
                        capital_impact = price_change_pct * position_size
                        
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': tp,
                            'price_pnl': price_change_pct,
                            'capital_pnl': capital_impact,
                            'reason': 'TP',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        break
                else:  # SHORT
                    if candle['high'] >= sl:
                        price_change_pct = ((entry - sl) / entry) * 100
                        capital_impact = price_change_pct * position_size
                        
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': sl,
                            'price_pnl': price_change_pct,
                            'capital_pnl': capital_impact,
                            'reason': 'SL',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        break
                    elif candle['low'] <= tp:
                        price_change_pct = ((entry - tp) / entry) * 100
                        capital_impact = price_change_pct * position_size
                        
                        trades.append({
                            'time': current['timestamp'],
                            'signal': signal,
                            'entry': entry,
                            'exit': tp,
                            'price_pnl': price_change_pct,
                            'capital_pnl': capital_impact,
                            'reason': 'TP',
                            'smc': smc_confirmed,
                            'position': position_size
                        })
                        break
    
    if not trades:
        log("\nNO TRADES")
        return
    
    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['price_pnl'] > 0])
    
    smc_trades = df_trades[df_trades['smc'] == True]
    normal_trades = df_trades[df_trades['smc'] == False]
    
    log("\n" + "="*70)
    log("RESULTS (FIXED PNL)")
    log("="*70)
    
    log(f"\n[OVERALL]")
    log(f"  Trades: {len(df_trades)}")
    log(f"  Wins: {wins} | Losses: {len(df_trades) - wins}")
    log(f"  Win Rate: {wins/len(df_trades)*100:.1f}%")
    
    log(f"\n[TRADE PNL] (Price Change)")
    log(f"  Total: {df_trades['price_pnl'].sum():.2f}%")
    log(f"  Average: {df_trades['price_pnl'].mean():.2f}%")
    log(f"  Max Win: {df_trades['price_pnl'].max():.2f}%")
    log(f"  Max Loss: {df_trades['price_pnl'].min():.2f}%")
    
    log(f"\n[CAPITAL IMPACT] (With Position Size)")
    log(f"  Total: {df_trades['capital_pnl'].sum():.2f}%")
    log(f"  Average: {df_trades['capital_pnl'].mean():.2f}%")
    
    log(f"\n[SMC BOOST]")
    log(f"  SMC Trades: {len(smc_trades)} ({len(smc_trades)/len(df_trades)*100:.1f}%)")
    log(f"  Normal Trades: {len(normal_trades)} ({len(normal_trades)/len(df_trades)*100:.1f}%)")
    
    if len(smc_trades) > 0:
        smc_wins = len(smc_trades[smc_trades['price_pnl'] > 0])
        log(f"\n  SMC Win Rate: {smc_wins/len(smc_trades)*100:.1f}%")
        log(f"  SMC Trade PNL: {smc_trades['price_pnl'].sum():.2f}%")
        log(f"  SMC Capital Impact: {smc_trades['capital_pnl'].sum():.2f}%")
    
    if len(normal_trades) > 0:
        normal_wins = len(normal_trades[normal_trades['price_pnl'] > 0])
        log(f"\n  Normal Win Rate: {normal_wins/len(normal_trades)*100:.1f}%")
        log(f"  Normal Trade PNL: {normal_trades['price_pnl'].sum():.2f}%")
        log(f"  Normal Capital Impact: {normal_trades['capital_pnl'].sum():.2f}%")
    
    log(f"\n[EXIT REASONS]")
    tp_count = len(df_trades[df_trades['reason'] == 'TP'])
    sl_count = len(df_trades[df_trades['reason'] == 'SL'])
    log(f"  TP: {tp_count} ({tp_count/len(df_trades)*100:.1f}%)")
    log(f"  SL: {sl_count} ({sl_count/len(df_trades)*100:.1f}%)")
    
    log("\n" + "="*70)
    log("COMPLETE")
    log("="*70)
    
    # 保存
    with open('silver_bullet_fixed_results.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print("\nSaved to: silver_bullet_fixed_results.txt")


if __name__ == "__main__":
    backtest_and_save()
