#!/usr/bin/env python3
# tools/backtest_both_strategies.py
"""
完整回測兩個策略（異步版本）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pandas_ta as ta
import asyncio
from datetime import datetime


def simple_backtest(df, strategy_name='Silver Bullet'):
    """
    簡化回測邏輯（直接用技術指標模擬）
    """
    print(f"\n{'='*70}")
    print(f"🎯 {strategy_name} 策略回測")
    print(f"{'='*70}")
    
    # 計算指標
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    trades = []
    
    for i in range(250, len(df)):
        current = df.iloc[i]
        prev_4h = df.iloc[i-4:i]
        
        # 檢查時段（如果需要）
        hour = current['timestamp'].hour + current['timestamp'].minute / 60.0
        
        if strategy_name == 'Silver Bullet':
            # Silver Bullet 邏輯
            # 時段：UTC 02-05 或 10-11（原版）
            in_session = (2 <= hour < 5) or (10 <= hour < 11)
            
            if not in_session:
                continue
            
            # 掃蕩形態
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
                
                # SMC 加碼模擬（假設40%確認率）
                import random
                smc_confirmed = random.random() < 0.4
                position_size = 0.03 if smc_confirmed else 0.02
                
                tp = entry + (abs(entry - sl) * 2.5) if signal == 'LONG' else entry - (abs(entry - sl) * 2.5)
                
                # 找出場
                for j in range(i+1, min(i+100, len(df))):
                    candle = df.iloc[j]
                    
                    if signal == 'LONG':
                        if candle['low'] <= sl:
                            pnl = ((sl - entry) / entry) * position_size * 100
                            trades.append({'time': current['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'SL', 'smc': smc_confirmed})
                            break
                        elif candle['high'] >= tp:
                            pnl = ((tp - entry) / entry) * position_size * 100
                            trades.append({'time': current['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'TP', 'smc': smc_confirmed})
                            break
                    else:
                        if candle['high'] >= sl:
                            pnl = ((entry - sl) / entry) * position_size * 100
                            trades.append({'time': current['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'SL', 'smc': smc_confirmed})
                            break
                        elif candle['low'] <= tp:
                            pnl = ((entry - tp) / entry) * position_size * 100
                            trades.append({'time': current['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'TP', 'smc': smc_confirmed})
                            break
    
    return pd.DataFrame(trades) if trades else None


def backtest_hybrid_sfp(df_15m):
    """Hybrid SFP 回測（4h）"""
    print(f"\n{'='*70}")
    print(f"🎯 Hybrid SFP 策略回測")
    print(f"{'='*70}")
    
    # 轉為 4h
    df_15m.set_index('timestamp', inplace=True)
    df_4h = df_15m.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df_4h.reset_index(inplace=True)
    
    # 計算指標
    df_4h['ema_200'] = ta.ema(df_4h['close'], length=200)
    df_4h['rsi'] = ta.rsi(df_4h['close'], length=14)
    df_4h['atr'] = ta.atr(df_4h['high'], df_4h['low'], df_4h['close'], length=14)
    df_4h['adx'] = ta.adx(df_4h['high'], df_4h['low'], df_4h['close'], length=14)['ADX_14']
    
    # Bollinger Bands
    bb = ta.bbands(df_4h['close'], length=20, std=2.0)
    if bb is not None:
        cols = bb.columns
        df_4h['bb_upper'] = bb[cols[cols.str.startswith('BBU')][0]]
        df_4h['bb_lower'] = bb[cols[cols.str.startswith('BBL')][0]]
        df_4h['bw'] = bb[cols[cols.str.startswith('BBB')][0]]
    
    df_4h['swing_high'] = df_4h['high'].rolling(50).max().shift(1)
    df_4h['swing_low'] = df_4h['low'].rolling(50).min().shift(1)
    
    trades = []
    
    for i in range(250, len(df_4h)):
        prev = df_4h.iloc[i-1]
        
        signal = None
        sl = None
        tp = None
        
        # SFP 偵測
        if prev['adx'] > 30:
            # Sweep High
            if prev['high'] > prev['swing_high'] and prev['close'] < prev['swing_high']:
                if prev['rsi'] > 60:
                    signal = 'SHORT'
                    sl = prev['high']
                    tp = prev['close'] - (prev['high'] - prev['close']) * 2.5
            
            # Sweep Low
            elif prev['low'] < prev['swing_low'] and prev['close'] > prev['swing_low']:
                if prev['rsi'] < 40:
                    signal = 'LONG'
                    sl = prev['low']
                    tp = prev['close'] + (prev['close'] - prev['low']) * 2.5
        
        # Trend Breakout
        if prev['adx'] > 25 and pd.notna(prev.get('bb_upper')):
            if prev['close'] > prev['bb_upper'] and prev['close'] > prev['ema_200'] and prev['bw'] > 5.0:
                signal = 'LONG'
                sl = prev['close'] - 2 * prev['atr']
                tp = prev['close'] + (2 * prev['atr']) * 2.5
        
        if signal:
            entry = prev['close']
            
            # 找出場
            for j in range(i, min(i+50, len(df_4h))):
                candle = df_4h.iloc[j]
                
                if signal == 'LONG':
                    if candle['low'] <= sl:
                        pnl = ((sl - entry) / entry) * 100
                        trades.append({'time': prev['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'SL'})
                        break
                    elif candle['high'] >= tp:
                        pnl = ((tp - entry) / entry) * 100
                        trades.append({'time': prev['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'TP'})
                        break
                else:
                    if candle['high'] >= sl:
                        pnl = ((entry - sl) / entry) * 100
                        trades.append({'time': prev['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'SL'})
                        break
                    elif candle['low'] <= tp:
                        pnl = ((entry - tp) / entry) * 100
                        trades.append({'time': prev['timestamp'], 'signal': signal, 'pnl': pnl, 'reason': 'TP'})
                        break
    
    return pd.DataFrame(trades) if trades else None


def main():
    print("="*70)
    print("🔬 完整策略回測")
    print("="*70)
    
    # 載入數據
    try:
        df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except:
        print("❌ 找不到數據文件: data/backtest/BTC_USDT_15m_2023-2024.csv")
        return
    
    print(f"\n數據範圍: {df.iloc[0]['timestamp']} 到 {df.iloc[-1]['timestamp']}")
    print(f"總K線數: {len(df)}")
    
    # 回測兩個策略
    sb_trades = simple_backtest(df.copy(), 'Silver Bullet')
    sfp_trades = backtest_hybrid_sfp(df.copy())
    
    # Silver Bullet 結果
    if sb_trades is not None and len(sb_trades) > 0:
        wins = len(sb_trades[sb_trades['pnl'] > 0])
        smc_count = len(sb_trades[sb_trades['smc'] == True])
        
        print(f"\n📊 Silver Bullet 統計：")
        print(f"   總交易: {len(sb_trades)}")
        print(f"   SMC 加碼: {smc_count} ({smc_count/len(sb_trades)*100:.1f}%)")
        print(f"   獲利: {wins}, 虧損: {len(sb_trades) - wins}")
        print(f"   勝率: {wins/len(sb_trades)*100:.1f}%")
        print(f"   總盈虧: {sb_trades['pnl'].sum():.2f}%")
        print(f"   平均: {sb_trades['pnl'].mean():.2f}%")
        print(f"   最大獲利: {sb_trades['pnl'].max():.2f}%")
        print(f"   最大虧損: {sb_trades['pnl'].min():.2f}%")
    else:
        print("\n❌ Silver Bullet 無交易")
    
    # Hybrid SFP 結果
    if sfp_trades is not None and len(sfp_trades) > 0:
        wins = len(sfp_trades[sfp_trades['pnl'] > 0])
        
        print(f"\n📊 Hybrid SFP 統計：")
        print(f"   總交易: {len(sfp_trades)}")
        print(f"   獲利: {wins}, 虧損: {len(sfp_trades) - wins}")
        print(f"   勝率: {wins/len(sfp_trades)*100:.1f}%")
        print(f"   總盈虧: {sfp_trades['pnl'].sum():.2f}%")
        print(f"   平均: {sfp_trades['pnl'].mean():.2f}%")
    else:
        print("\n❌ Hybrid SFP 無交易")
    
    # 對比
    print(f"\n{'='*70}")
    print("📊 策略對比")
    print(f"{'='*70}")
    
    if sb_trades is not None and sfp_trades is not None:
        print(f"\n{'策略':<20} {'交易數':<10} {'勝率':<10} {'總盈虧':<10}")
        print("-"*70)
        
        sb_wr = len(sb_trades[sb_trades['pnl']>0])/len(sb_trades)*100 if len(sb_trades)>0 else 0
        sfp_wr = len(sfp_trades[sfp_trades['pnl']>0])/len(sfp_trades)*100 if len(sfp_trades)>0 else 0
        
        print(f"{'Silver Bullet':<20} {len(sb_trades):<10} {sb_wr:<10.1f}% {sb_trades['pnl'].sum():<10.2f}%")
        print(f"{'Hybrid SFP':<20} {len(sfp_trades):<10} {sfp_wr:<10.1f}% {sfp_trades['pnl'].sum():<10.2f}%")


if __name__ == "__main__":
    main()
