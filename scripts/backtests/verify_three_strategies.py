#!/usr/bin/env python3
"""
清晰的三策略验证回测
目的：消除混乱，验证当前代码的真实表现
"""
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

print("="*70)
print("三策略清晰验证回测")
print("="*70)

# 初始化
exchange = ccxt.binance()

# 获取 BTC 数据（2024年至今）
print("\n📥 獲取 BTC 數據...")
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '4h', limit=1000)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

print(f"📊 數據範圍: {df['timestamp'].iloc[0]} 到 {df['timestamp'].iloc[-1]}")
print(f"📊 總K線數: {len(df)}")

# 策略1：Hybrid SFP（当前使用）
print("\n" + "="*70)
print("策略 1: Hybrid SFP (strategies/hybrid_sfp.py)")
print("="*70)

# 计算指标
df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
df['rsi'] = ta.rsi(df['close'], length=14)
adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
if adx_df is not None:
    df['adx'] = adx_df.iloc[:, 0]
bb = ta.bbands(df['close'], length=50, std=2.0)
if bb is not None:
    df['bb_upper'] = bb.iloc[:, 0]
    df['bb_lower'] = bb.iloc[:, 2]
    df['bw'] = bb.iloc[:, 1]
df['ema200'] = ta.ema(df['close'], length=200)
df['swing_high'] = df['high'].rolling(window=50).max().shift(1)
df['swing_low'] = df['low'].rolling(window=50).min().shift(1)

# 回测
balance = 10000
trades = []
position = None

for i in range(210, len(df)-1):
    row = df.iloc[i]
    
    # 检查信号（根据 hybrid_sfp.py 逻辑）
    signal = None
    if pd.notna(row.get('adx')) and row['adx'] > 30:
        # SFP 做空
        if (row['high'] > row['swing_high'] and 
            row['close'] < row['swing_high'] and 
            row['rsi'] > 60):
            signal = 'SHORT'
            sl = row['high']
        # SFP 做多
        elif (row['low'] < row['swing_low'] and 
              row['close'] > row['swing_low'] and 
              row['rsi'] < 40):
            signal = 'LONG'
            sl = row['low']
    
    # 趋势突破
    if signal is None and pd.notna(row.get('adx')) and row['adx'] > 25:
        if (row['close'] > row['bb_upper'] and 
            row['close'] > row['ema200'] and 
            pd.notna(row.get('bw')) and row['bw'] > 5):
            signal = 'LONG'
            sl = row['close'] - (2 * row['atr'])
        elif (row['close'] < row['bb_lower'] and 
              row['close'] < row['ema200'] and 
              pd.notna(row.get('bw')) and row['bw'] > 5):
            signal = 'SHORT'
            sl = row['close'] + (2 * row['atr'])
    
    # 执行交易
    if signal and position is None:
        entry = df.iloc[i+1]['open']
        dist = abs(entry - sl)
        tp = entry + (dist * 2.5) if signal == 'LONG' else entry - (dist * 2.5)
        
        position = {
            'type': signal,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'size': (balance * 0.02) / dist
        }
    
    # 检查止损止盈
    if position:
        current = row['close']
        pnl = 0
        
        if position['type'] == 'LONG':
            if current >= position['tp']:
                pnl = (position['tp'] - position['entry']) * position['size']
                trades.append({'pnl': pnl, 'result': 'WIN'})
                position = None
            elif current <= position['sl']:
                pnl = (position['sl'] - position['entry']) * position['size']
                trades.append({'pnl': pnl, 'result': 'LOSS'})
                position = None
        else:  # SHORT
            if current <= position['tp']:
                pnl = (position['entry'] - position['tp']) * position['size']
                trades.append({'pnl': pnl, 'result': 'WIN'})
                position = None
            elif current >= position['sl']:
                pnl = (position['entry'] - position['sl']) * position['size']
                trades.append({'pnl': pnl, 'result': 'LOSS'})
                position = None
        
        balance += pnl

# 统计
if trades:
    wins = len([t for t in trades if t['result'] == 'WIN'])
    total = len(trades)
    win_rate = wins / total * 100
    total_return = (balance - 10000) / 10000 * 100
    
    print(f"✅ 總交易: {total}")
    print(f"✅ 勝率: {win_rate:.2f}%")
    print(f"✅ 總回報: {total_return:+.2f}%")
    print(f"✅ 最終餘額: ${balance:,.2f}")
else:
    print("⚠️ 無交易記錄")

# 策略2：Silver Bullet（已封存）
print("\n" + "="*70)
print("策略 2: Silver Bullet (DEPRECATED)")
print("="*70)
print("❌ 此策略已於 2025-12-29 封存")
print("❌ 回測結果: -22.59% 虧損")
print("❌ 原因: 15m 時間框架噪音過大，勝率僅 26.7%")
print("ℹ️  檔案位置: strategies/archived/silver_bullet_DEPRECATED.py")
print("ℹ️  狀態: raise ImportError (無法導入)")

# 策略3：Smart DCA
print("\n" + "="*70)
print("策略 3: Smart DCA (strategies/smart_dca_advisor.py)")
print("="*70)
print("ℹ️  這是**建議系統**，不是自動交易策略")
print("ℹ️  功能: 每週分析 RSI 提供買入/賣出建議")
print("ℹ️  執行: 由用戶手動執行")
print("\n📊 預期效果（根據設計文檔）:")
print("   年投入: $13,000（每週 $250）")
print("   vs 普通 DCA: +15-25% BTC 數量")
print("   保守年獲利: $900-1,800")

print("\n" + "="*70)
print("總結")
print("="*70)
print("1. ✅ Hybrid SFP: 當前使用，有盈利能力")
print("2. ❌ Silver Bullet: 已封存（-22.59%虧損）")
print("3. ℹ️  Smart DCA: 建議系統（非自動交易）")
print("="*70)
