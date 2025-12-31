#!/usr/bin/env python3
"""
多幣種回測（穩定版）
修正：
1. 加入延遲避免 API 限流
2. 處理錯誤幣種
3. 確認多空邏輯正確
"""
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import time

print("="*70)
print("Hybrid SFP 多幣種回測（穩定版）")
print("="*70)

# 配置
ORIGINAL_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT']
EXTENDED_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT',
    'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
    'UNI/USDT', 'ATOM/USDT', 'LTC/USDT'  # 移除 APT, ARB（可能數據不足）
]

exchange = ccxt.binance()

def calculate_indicators(df):
    """計算技術指標"""
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
    return df

def check_signal(row):
    """檢查交易信號（多空雙向）"""
    signal = None
    sl = None
    
    # SFP 策略（可做多或做空）
    if pd.notna(row.get('adx')) and row['adx'] > 30:
        # 做空信號
        if (row['high'] > row['swing_high'] and 
            row['close'] < row['swing_high'] and 
            row['rsi'] > 60):
            signal = 'SHORT'
            sl = row['high']
        # 做多信號
        elif (row['low'] < row['swing_low'] and 
              row['close'] > row['swing_low'] and 
              row['rsi'] < 40):
            signal = 'LONG'
            sl = row['low']
    
    # 趨勢突破（可做多或做空）
    if signal is None and pd.notna(row.get('adx')) and row['adx'] > 25:
        # 做多突破
        if (row['close'] > row['bb_upper'] and 
            row['close'] > row['ema200'] and 
            pd.notna(row.get('bw')) and row['bw'] > 5):
            signal = 'LONG'
            sl = row['close'] - (2 * row['atr'])
        # 做空突破
        elif (row['close'] < row['bb_lower'] and 
              row['close'] < row['ema200'] and 
              pd.notna(row.get('bw')) and row['bw'] > 5):
            signal = 'SHORT'
            sl = row['close'] + (2 * row['atr'])
    
    return signal, sl

def backtest_single_symbol(symbol, limit=500):
    """單一幣種回測（支援多空）"""
    try:
        # 加入延遲避免限流
        time.sleep(0.5)
        
        ohlcv = exchange.fetch_ohlcv(symbol, '4h', limit=limit)
        if not ohlcv or len(ohlcv) < 250:
            return []
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = calculate_indicators(df)
        
        trades = []
        position = None  # None 表示無倉位
        long_count = 0
        short_count = 0
        
        for i in range(210, len(df)-1):
            row = df.iloc[i]
            signal, sl = check_signal(row)
            
            # 開倉（同一時間只能有一個倉位）
            if signal and position is None:
                entry = df.iloc[i+1]['open']
                dist = abs(entry - sl)
                if dist == 0:
                    continue
                tp = entry + (dist * 2.5) if signal == 'LONG' else entry - (dist * 2.5)
                position = {
                    'type': signal,
                    'entry': entry,
                    'sl': sl,
                    'tp': tp,
                }
                
                if signal == 'LONG':
                    long_count += 1
                else:
                    short_count += 1
            
            # 檢查平倉
            if position:
                current = row['close']
                
                if position['type'] == 'LONG':
                    # 做多止盈
                    if current >= position['tp']:
                        pnl = (position['tp'] - position['entry']) / position['entry']
                        trades.append({
                            'symbol': symbol,
                            'type': 'LONG',
                            'pnl': pnl,
                            'result': 'WIN'
                        })
                        position = None
                    # 做多止損
                    elif current <= position['sl']:
                        pnl = (position['sl'] - position['entry']) / position['entry']
                        trades.append({
                            'symbol': symbol,
                            'type': 'LONG',
                            'pnl': pnl,
                            'result': 'LOSS'
                        })
                        position = None
                else:  # SHORT
                    # 做空止盈
                    if current <= position['tp']:
                        pnl = (position['entry'] - position['tp']) / position['entry']
                        trades.append({
                            'symbol': symbol,
                            'type': 'SHORT',
                            'pnl': pnl,
                            'result': 'WIN'
                        })
                        position = None
                    # 做空止損
                    elif current >= position['sl']:
                        pnl = (position['entry'] - position['sl']) / position['entry']
                        trades.append({
                            'symbol': symbol,
                            'type': 'SHORT',
                            'pnl': pnl,
                            'result': 'LOSS'
                        })
                        position = None
        
        return trades, long_count, short_count
    except Exception as e:
        print(f"  錯誤: {e}")
        return [], 0, 0

def run_backtest(symbols, name):
    """運行多幣種回測"""
    print(f"\n{'='*70}")
    print(f"{name}（{len(symbols)} 個幣種）")
    print(f"{'='*70}")
    
    all_trades = []
    total_long = 0
    total_short = 0
    
    for i, symbol in enumerate(symbols, 1):
        print(f"  [{i:2d}/{len(symbols)}] {symbol:12s}...", end=' ')
        trades, long, short = backtest_single_symbol(symbol)
        all_trades.extend(trades)
        total_long += long
        total_short += short
        print(f"✓ {len(trades):3d} 筆 (多{long}/空{short})")
    
    # 統計
    if all_trades:
        total = len(all_trades)
        wins = len([t for t in all_trades if t['result'] == 'WIN'])
        win_rate = wins / total * 100
        total_pnl = sum(t['pnl'] for t in all_trades)
        
        long_trades = [t for t in all_trades if t['type'] == 'LONG']
        short_trades = [t for t in all_trades if t['type'] == 'SHORT']
        
        print(f"\n📊 回測結果：")
        print(f"  總交易數：{total} 筆")
        print(f"  多/空分佈：{len(long_trades)} 多 / {len(short_trades)} 空")
        print(f"  勝率：{win_rate:.2f}%（{wins}勝/{total-wins}負）")
        print(f"  總報酬：{total_pnl*100:+.2f}%")
        
        if long_trades:
            long_wins = len([t for t in long_trades if t['result'] == 'WIN'])
            long_winrate = long_wins / len(long_trades) * 100
            long_pnl = sum(t['pnl'] for t in long_trades) * 100
            print(f"  做多績效：勝率 {long_winrate:.1f}%，報酬 {long_pnl:+.2f}%")
        
        if short_trades:
            short_wins = len([t for t in short_trades if t['result'] == 'WIN'])
            short_winrate = short_wins / len(short_trades) * 100
            short_pnl = sum(t['pnl'] for t in short_trades) * 100
            print(f"  做空績效：勝率 {short_winrate:.1f}%，報酬 {short_pnl:+.2f}%")
        
        return {
            'total_trades': total,
            'win_rate': win_rate,
            'total_return': total_pnl * 100,
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
        }
    else:
        print("  ⚠️ 無交易記錄")
        return None

# 執行回測
print(f"\n開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

result_original = run_backtest(ORIGINAL_SYMBOLS, "原版（5幣種）")
result_extended = run_backtest(EXTENDED_SYMBOLS, "擴展版（13幣種）")

# 對比
if result_original and result_extended:
    print(f"\n{'='*70}")
    print("對比分析")
    print(f"{'='*70}\n")
    
    print(f"{'指標':<15} {'原版':<15} {'擴展版':<15} {'變化':<15}")
    print("-" * 60)
    print(f"{'總交易數':<15} {result_original['total_trades']:<15} {result_extended['total_trades']:<15} {result_extended['total_trades']-result_original['total_trades']:+} 筆")
    print(f"{'勝率':<15} {result_original['win_rate']:<15.2f} {result_extended['win_rate']:<15.2f} {result_extended['win_rate']-result_original['win_rate']:+.2f}%")
    print(f"{'總報酬':<15} {result_original['total_return']:<15.2f} {result_extended['total_return']:<15.2f} {result_extended['total_return']-result_original['total_return']:+.2f}%")
    print(f"{'多單數':<15} {result_original['long_trades']:<15} {result_extended['long_trades']:<15}")
    print(f"{'空單數':<15} {result_original['short_trades']:<15} {result_extended['short_trades']:<15}")

print(f"\n{'='*70}")
print(f"完成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}")
