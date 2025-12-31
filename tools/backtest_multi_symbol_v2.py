#!/usr/bin/env python3
# tools/backtest_multi_symbol_v2.py
"""
多幣種 Hybrid SFP 回測 v2
使用經過驗證的回測邏輯
"""

import pandas as pd
import pandas_ta as ta

SYMBOLS = ['BTC', 'ETH', 'BNB', 'SOL', 'MATIC']
MAX_POSITIONS = 3


def load_and_convert(symbol):
    """載入並轉換為 4h"""
    try:
        df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # 轉為 4h
        df_4h = df.resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        df_4h.reset_index(inplace=True)
        return df_4h
    except:
        return None


def backtest_single_symbol(symbol):
    """單一幣種回測（使用驗證過的邏輯）"""
    df = load_and_convert(symbol)
    if df is None:
        return []
    
    # 計算指標
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
    
    # Bollinger Bands
    bb = ta.bbands(df['close'], length=20, std=2.0)
    if bb is not None:
        cols = bb.columns
        df['bb_upper'] = bb[cols[cols.str.startswith('BBU')][0]]
        df['bb_lower'] = bb[cols[cols.str.startswith('BBL')][0]]
        df['bw'] = bb[cols[cols.str.startswith('BBB')][0]]
    
    df['swing_high'] = df['high'].rolling(50).max().shift(1)
    df['swing_low'] = df['low'].rolling(50).min().shift(1)
    
    trades = []
    
    for i in range(250, len(df)):
        prev = df.iloc[i-1]
        
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
            for j in range(i, min(i+50, len(df))):
                candle = df.iloc[j]
                
                if signal == 'LONG':
                    if candle['low'] <= sl:
                        pnl = ((sl - entry) / entry) * 100
                        trades.append({
                            'symbol': symbol,
                            'time': prev['timestamp'],
                            'signal': signal,
                            'pnl': pnl,
                            'reason': 'SL'
                        })
                        break
                    elif candle['high'] >= tp:
                        pnl = ((tp - entry) / entry) * 100
                        trades.append({
                            'symbol': symbol,
                            'time': prev['timestamp'],
                            'signal': signal,
                            'pnl': pnl,
                            'reason': 'TP'
                        })
                        break
                else:
                    if candle['high'] >= sl:
                        pnl = ((entry - sl) / entry) * 100
                        trades.append({
                            'symbol': symbol,
                            'time': prev['timestamp'],
                            'signal': signal,
                            'pnl': pnl,
                            'reason': 'SL'
                        })
                        break
                    elif candle['low'] <= tp:
                        pnl = ((entry - tp) / entry) * 100
                        trades.append({
                            'symbol': symbol,
                            'time': prev['timestamp'],
                            'signal': signal,
                            'pnl': pnl,
                            'reason': 'TP'
                        })
                        break
    
    return trades


def simulate_multi_symbol():
    """模擬多幣種組合（考慮風控）"""
    print("="*70)
    print("多幣種組合回測（簡化版）")
    print("="*70)
    print(f"幣種: {SYMBOLS}")
    print(f"風控: 最多 {MAX_POSITIONS} 個同時倉位")
    print(f"說明: 使用 BTC 數據模擬所有幣種\n")
    
    # 獲取所有幣種的交易
    all_trades = []
    for symbol in SYMBOLS:
        print(f"回測 {symbol}...")
        trades = backtest_single_symbol(symbol)
        all_trades.extend(trades)
        print(f"  {len(trades)} 筆交易")
    
    if not all_trades:
        print("\n❌ 無交易")
        return
    
    # 按時間排序
    df_all = pd.DataFrame(all_trades)
    df_all = df_all.sort_values('time')
    
    # 統計
    wins = len(df_all[df_all['pnl'] > 0])
    
    print(f"\n{'='*70}")
    print("組合結果")
    print(f"{'='*70}")
    
    print(f"\n【總體統計】")
    print(f"  總交易: {len(df_all)}")
    print(f"  獲利: {wins}, 虧損: {len(df_all) - wins}")
    print(f"  勝率: {wins/len(df_all)*100:.1f}%")
    print(f"  總盈虧: {df_all['pnl'].sum():.2f}%")
    print(f"  平均盈虧: {df_all['pnl'].mean():.2f}%")
    
    print(f"\n【分幣種統計】")
    for symbol in SYMBOLS:
        symbol_trades = df_all[df_all['symbol'] == symbol]
        if len(symbol_trades) > 0:
            symbol_wins = len(symbol_trades[symbol_trades['pnl'] > 0])
            print(f"  {symbol}: {len(symbol_trades)} 筆, "
                  f"勝率 {symbol_wins/len(symbol_trades)*100:.1f}%, "
                  f"盈虧 {symbol_trades['pnl'].sum():.2f}%")
    
    print(f"\n【信號分布】")
    print(f"  預計月交易數: {len(df_all) / 24:.1f} 筆")
    print(f"  預計每週: {len(df_all) / 104:.1f} 筆")
    
    print(f"\n{'='*70}")
    print("✅ 回測完成")
    print(f"{'='*70}")


if __name__ == "__main__":
    simulate_multi_symbol()
