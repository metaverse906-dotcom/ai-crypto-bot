#!/usr/bin/env python3
"""
多幣種版本對比回測
對比原版（5幣種）vs 擴展版（15幣種）
"""
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import asyncio

print("="*70)
print("Hybrid SFP 多幣種版本對比回測")
print("="*70)

# 配置
ORIGINAL_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT']
EXTENDED_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT',
    'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
    'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'APT/USDT', 'ARB/USDT'
]

# 初始化
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
    """檢查交易信號"""
    signal = None
    sl = None
    
    # SFP 策略
    if pd.notna(row.get('adx')) and row['adx'] > 30:
        if (row['high'] > row['swing_high'] and 
            row['close'] < row['swing_high'] and 
            row['rsi'] > 60):
            signal = 'SHORT'
            sl = row['high']
        elif (row['low'] < row['swing_low'] and 
              row['close'] > row['swing_low'] and 
              row['rsi'] < 40):
            signal = 'LONG'
            sl = row['low']
    
    # 趨勢突破
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
    
    return signal, sl

def backtest_single_symbol(symbol, limit=500):
    """單一幣種回測"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, '4h', limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = calculate_indicators(df)
        
        trades = []
        position = None
        
        for i in range(210, len(df)-1):
            row = df.iloc[i]
            signal, sl = check_signal(row)
            
            # 開倉
            if signal and position is None:
                entry = df.iloc[i+1]['open']
                dist = abs(entry - sl)
                tp = entry + (dist * 2.5) if signal == 'LONG' else entry - (dist * 2.5)
                position = {
                    'type': signal,
                    'entry': entry,
                    'sl': sl,
                    'tp': tp,
                    'size': 1
                }
            
            # 檢查平倉
            if position:
                current = row['close']
                pnl = 0
                
                if position['type'] == 'LONG':
                    if current >= position['tp']:
                        pnl = (position['tp'] - position['entry']) / position['entry']
                        trades.append({'symbol': symbol, 'pnl': pnl, 'result': 'WIN'})
                        position = None
                    elif current <= position['sl']:
                        pnl = (position['sl'] - position['entry']) / position['entry']
                        trades.append({'symbol': symbol, 'pnl': pnl, 'result': 'LOSS'})
                        position = None
                else:
                    if current <= position['tp']:
                        pnl = (position['entry'] - position['tp']) / position['entry']
                        trades.append({'symbol': symbol, 'pnl': pnl, 'result': 'WIN'})
                        position = None
                    elif current >= position['sl']:
                        pnl = (position['entry'] - position['sl']) / position['entry']
                        trades.append({'symbol': symbol, 'pnl': pnl, 'result': 'LOSS'})
                        position = None
        
        return trades
    except Exception as e:
        print(f"  {symbol}: 錯誤 - {e}")
        return []

def run_backtest(symbols, name):
    """運行多幣種回測"""
    print(f"\n{'='*70}")
    print(f"回測：{name}（{len(symbols)} 個幣種）")
    print(f"{'='*70}")
    
    all_trades = []
    for i, symbol in enumerate(symbols, 1):
        print(f"  [{i}/{len(symbols)}] 回測 {symbol}...", end=' ')
        trades = backtest_single_symbol(symbol)
        all_trades.extend(trades)
        print(f"✓ ({len(trades)} 筆交易)")
    
    # 統計
    if all_trades:
        total = len(all_trades)
        wins = len([t for t in all_trades if t['result'] == 'WIN'])
        win_rate = wins / total * 100
        total_pnl = sum(t['pnl'] for t in all_trades)
        avg_win = sum(t['pnl'] for t in all_trades if t['result'] == 'WIN') / wins if wins > 0 else 0
        losses = total - wins
        avg_loss = sum(t['pnl'] for t in all_trades if t['result'] == 'LOSS') / losses if losses > 0 else 0
        
        print(f"\n📊 回測結果：")
        print(f"  總交易數：{total}")
        print(f"  勝率：{win_rate:.2f}%（{wins}勝/{losses}負）")
        print(f"  總報酬：{total_pnl*100:+.2f}%")
        print(f"  平均獲利：{avg_win*100:+.2f}%")
        print(f"  平均虧損：{avg_loss*100:.2f}%")
        print(f"  盈虧比：{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "  盈虧比：N/A")
        
        # 每幣種分佈
        symbol_stats = {}
        for symbol in symbols:
            symbol_trades = [t for t in all_trades if t['symbol'] == symbol]
            if symbol_trades:
                symbol_stats[symbol] = len(symbol_trades)
        
        print(f"\n  每幣種交易分佈：")
        for symbol, count in sorted(symbol_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"    {symbol}: {count} 筆")
        
        return {
            'total_trades': total,
            'win_rate': win_rate,
            'total_return': total_pnl * 100,
            'avg_win': avg_win * 100,
            'avg_loss': avg_loss * 100,
            'trades': all_trades
        }
    else:
        print("  ⚠️ 無交易記錄")
        return None

# 執行回測
print(f"\n開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

result_original = run_backtest(ORIGINAL_SYMBOLS, "原版（5幣種）")
result_extended = run_backtest(EXTENDED_SYMBOLS, "擴展版（15幣種）")

# 對比分析
print(f"\n{'='*70}")
print("對比分析")
print(f"{'='*70}")

if result_original and result_extended:
    print(f"\n指標對比：")
    print(f"{'指標':<20} {'原版（5幣種）':<20} {'擴展版（15幣種）':<20} {'變化':<15}")
    print("-" * 75)
    
    metrics = [
        ('總交易數', 'total_trades', '筆'),
        ('勝率', 'win_rate', '%'),
        ('總報酬', 'total_return', '%'),
        ('平均獲利', 'avg_win', '%'),
        ('平均虧損', 'avg_loss', '%'),
    ]
    
    for name, key, unit in metrics:
        orig = result_original[key]
        ext = result_extended[key]
        if key == 'total_trades':
            change = f"+{ext - orig} 筆"
        else:
            change = f"{((ext / orig - 1) * 100):+.1f}%" if orig != 0 else "N/A"
        
        if unit == '%':
            print(f"{name:<20} {orig:<20.2f} {ext:<20.2f} {change:<15}")
        else:
            print(f"{name:<20} {orig:<20.0f} {ext:<20.0f} {change:<15}")
    
    print(f"\n結論：")
    if result_extended['total_return'] > result_original['total_return']:
        diff = result_extended['total_return'] - result_original['total_return']
        print(f"  ✅ 擴展版總報酬較高（+{diff:.2f}%）")
    else:
        diff = result_original['total_return'] - result_extended['total_return']
        print(f"  ⚠️ 原版總報酬較高（+{diff:.2f}%）")
    
    if result_extended['win_rate'] > result_original['win_rate']:
        diff = result_extended['win_rate'] - result_original['win_rate']
        print(f"  ✅ 擴展版勝率較高（+{diff:.2f}%）")
    else:
        diff = result_original['win_rate'] - result_extended['win_rate']
        print(f"  ⚠️ 原版勝率較高（+{diff:.2f}%）")
    
    trades_increase = ((result_extended['total_trades'] / result_original['total_trades']) - 1) * 100
    print(f"  ℹ️  交易數量增加 {trades_increase:.1f}%")

print(f"\n{'='*70}")
print(f"回測完成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}")
