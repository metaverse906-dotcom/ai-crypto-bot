#!/usr/bin/env python3
# tools/test_optimized_strategies.py
"""
測試優化後的策略績效
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pandas_ta as ta
from datetime import datetime
from strategies.silver_bullet import SilverBulletStrategy
from strategies.hybrid_sfp import HybridSFPStrategy


class MockExecutor:
    """模擬執行器"""
    def __init__(self, symbol):
        self.symbol = symbol


def load_data():
    """載入 BTC 2023-2024 數據"""
    try:
        df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except:
        print("❌ 找不到數據文件")
        return None


def backtest_silver_bullet(df):
    """回測 Silver Bullet 策略"""
    print("\n" + "=" * 70)
    print("🎯 Silver Bullet 策略回測（優化版）")
    print("=" * 70)
    
    executor = MockExecutor('BTC/USDT')
    strategy = SilverBulletStrategy(executor)
    
    trades = []
    total_signals = 0
    smc_boosted = 0
    
    for i in range(250, len(df)):
        row = df.iloc[i]
        df_sub = df.iloc[max(0, i-250):i+1].copy()
        
        # 生成信號（同步模擬）
        signal = strategy.check_signal_sync(df_sub)
        
        if signal and signal.get('signal'):
            total_signals += 1
            position_size = signal.get('position_size_pct', 0.02)
            
            if position_size > 0.02:
                smc_boosted += 1
            
            # 模擬交易
            entry = signal['entry']
            sl = signal['sl']
            tp = signal['tp']
            
            # 找出場點
            exit_price = None
            exit_reason = None
            
            for j in range(i+1, min(i+100, len(df))):
                candle = df.iloc[j]
                
                if signal['signal'] == 'LONG':
                    if candle['low'] <= sl:
                        exit_price = sl
                        exit_reason = 'SL'
                        break
                    elif candle['high'] >= tp:
                        exit_price = tp
                        exit_reason = 'TP'
                        break
                else:  # SHORT
                    if candle['high'] >= sl:
                        exit_price = sl
                        exit_reason = 'SL'
                        break
                    elif candle['low'] <= tp:
                        exit_price = tp
                        exit_reason = 'TP'
                        break
            
            if exit_price:
                pnl_pct = ((exit_price - entry) / entry) if signal['signal'] == 'LONG' else ((entry - exit_price) / entry)
                pnl = pnl_pct * position_size * 100  # 基於倉位大小
                
                trades.append({
                    'entry_time': row['timestamp'],
                    'signal': signal['signal'],
                    'entry': entry,
                    'exit': exit_price,
                    'pnl_pct': pnl_pct * 100,
                    'pnl': pnl,
                    'position_size': position_size,
                    'reason': exit_reason,
                    'smc_boost': position_size > 0.02
                })
    
    # 統計
    if trades:
        df_trades = pd.DataFrame(trades)
        wins = len(df_trades[df_trades['pnl'] > 0])
        losses = len(df_trades[df_trades['pnl'] < 0])
        
        print(f"\n📊 交易統計：")
        print(f"   總信號數: {total_signals}")
        print(f"   SMC 加碼: {smc_boosted} ({smc_boosted/total_signals*100:.1f}%)")
        print(f"   總交易: {len(df_trades)}")
        print(f"   獲利: {wins}, 虧損: {losses}")
        print(f"   勝率: {wins/len(df_trades)*100:.1f}%")
        print(f"   總盈虧: {df_trades['pnl'].sum():.2f}%")
        print(f"   平均盈虧: {df_trades['pnl'].mean():.2f}%")
        print(f"   最大單筆獲利: {df_trades['pnl'].max():.2f}%")
        print(f"   最大單筆虧損: {df_trades['pnl'].min():.2f}%")
        
        return df_trades
    else:
        print("\n❌ 無交易紀錄")
        return None


def backtest_hybrid_sfp(df_15m):
    """回測 Hybrid SFP 策略"""
    print("\n" + "=" * 70)
    print("🎯 Hybrid SFP 策略回測")
    print("=" * 70)
    
    # 轉換為 4h
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m.set_index('timestamp', inplace=True)
    
    df_4h = df_15m.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_4h.reset_index(inplace=True)
    
    print(f"   數據: {len(df_4h)} 根 4h K線")
    
    executor = MockExecutor('BTC/USDT')
    strategy = HybridSFPStrategy(executor)
    
    trades = []
    
    for i in range(250, len(df_4h)):
        df_sub = df_4h.iloc[max(0, i-250):i+1].copy()
        
        signal = strategy.check_signal_sync(df_sub)
        
        if signal and signal.get('signal'):
            row = df_4h.iloc[i]
            entry = signal['entry']
            sl = signal['sl']
            tp = signal['tp']
            
            # 找出場
            exit_price = None
            exit_reason = None
            
            for j in range(i+1, min(i+50, len(df_4h))):
                candle = df_4h.iloc[j]
                
                if signal['signal'] == 'LONG':
                    if candle['low'] <= sl:
                        exit_price = sl
                        exit_reason = 'SL'
                        break
                    elif candle['high'] >= tp:
                        exit_price = tp
                        exit_reason = 'TP'
                        break
                else:
                    if candle['high'] >= sl:
                        exit_price = sl
                        exit_reason = 'SL'
                        break
                    elif candle['low'] <= tp:
                        exit_price = tp
                        exit_reason = 'TP'
                        break
            
            if exit_price:
                pnl_pct = ((exit_price - entry) / entry) if signal['signal'] == 'LONG' else ((entry - exit_price) / entry)
                
                trades.append({
                    'entry_time': row['timestamp'],
                    'signal': signal['signal'],
                    'entry': entry,
                    'exit': exit_price,
                    'pnl_pct': pnl_pct * 100,
                    'reason': exit_reason
                })
    
    # 統計
    if trades:
        df_trades = pd.DataFrame(trades)
        wins = len(df_trades[df_trades['pnl_pct'] > 0])
        
        print(f"\n📊 交易統計：")
        print(f"   總交易: {len(df_trades)}")
        print(f"   獲利: {wins}, 虧損: {len(df_trades) - wins}")
        print(f"   勝率: {wins/len(df_trades)*100:.1f}%")
        print(f"   總盈虧: {df_trades['pnl_pct'].sum():.2f}%")
        print(f"   平均盈虧: {df_trades['pnl_pct'].mean():.2f}%")
        
        return df_trades
    else:
        print("\n❌ 無交易紀錄")
        return None


def main():
    print("=" * 70)
    print("🔬 策略優化回測")
    print("=" * 70)
    
    df = load_data()
    if df is None:
        return
    
    print(f"\n數據範圍: {df.iloc[0]['timestamp']} 到 {df.iloc[-1]['timestamp']}")
    print(f"總K線數: {len(df)}")
    
    # 回測兩個策略
    sb_trades = backtest_silver_bullet(df.copy())
    sfp_trades = backtest_hybrid_sfp(df.copy())
    
    # 總結
    print("\n" + "=" * 70)
    print("📊 策略對比")
    print("=" * 70)
    
    if sb_trades is not None and sfp_trades is not None:
        print(f"\nSilver Bullet: {len(sb_trades)} 筆，勝率 {len(sb_trades[sb_trades['pnl']>0])/len(sb_trades)*100:.1f}%")
        print(f"Hybrid SFP: {len(sfp_trades)} 筆，勝率 {len(sfp_trades[sfp_trades['pnl_pct']>0])/len(sfp_trades)*100:.1f}%")


if __name__ == "__main__":
    main()
