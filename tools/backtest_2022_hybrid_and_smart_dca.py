#!/usr/bin/env python3
# tools/backtest_2022_hybrid_and_smart_dca.py
"""
完整回測：
1. 2022 Hybrid SFP 熊市表現
2. Smart DCA 三版本對比
"""

import pandas as pd
import pandas_ta as ta

# ========== Part 1: Hybrid SFP 熊市回測 ==========

def backtest_hybrid_2022():
    """測試 Hybrid SFP 在2022熊市表現"""
    print("="*70)
    print("Hybrid SFP - 2022 熊市回測")
    print("="*70)
    
    try:
        # 載入2022數據
        df = pd.read_csv('data/backtest/BTC_USDT_1h_2022.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except:
        print("❌ 找不到2022數據，請先運行 download_2022_data.py")
        return None
    
    print(f"\n期間: {df.iloc[0]['timestamp']} 到 {df.iloc[-1]['timestamp']}")
    print(f"K線數: {len(df)}")
    print(f"價格範圍: ${df['low'].min():.0f} - ${df['high'].max():.0f}")
    
    # 轉4h
    df.set_index('timestamp', inplace=True)
    df_4h = df.resample('4h').agg({
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
    
    bb = ta.bbands(df_4h['close'], length=20, std=2.0)
    if bb is not None:
        df_4h['bb_upper'] = bb.iloc[:, 0]
        df_4h['bb_lower'] = bb.iloc[:, 2]
        df_4h['bw'] = bb.iloc[:, 3]
    
    df_4h['swing_high'] = df_4h['high'].rolling(50).max().shift(1)
    df_4h['swing_low'] = df_4h['low'].rolling(50).min().shift(1)
    
    # 回測
    trades = []
    for i in range(250, len(df_4h)):
        prev = df_4h.iloc[i-1]
        
        signal = None
        sl = None
        
        # SFP
        if prev['adx'] > 30:
            if prev['high'] > prev['swing_high'] and prev['close'] < prev['swing_high']:
                if prev['rsi'] > 60:
                    signal = 'SHORT'
                    sl = prev['high']
            elif prev['low'] < prev['swing_low'] and prev['close'] > prev['swing_low']:
                if prev['rsi'] < 40:
                    signal = 'LONG'
                    sl = prev['low']
        
        # 趨勢突破
        if signal is None and prev['adx'] > 25:
            if prev['close'] > prev['bb_upper'] and prev['close'] > prev['ema_200'] and prev['bw'] > 5.0:
                signal = 'LONG'
                sl = prev['close'] - 2 * prev['atr']
        
        if signal:
            entry = prev['close']
            tp = entry + (abs(entry - sl) * 2.5) if signal == 'LONG' else entry - (abs(entry - sl) * 2.5)
            
            # 找出場
            for j in range(i, min(i+50, len(df_4h))):
                candle = df_4h.iloc[j]
                
                if signal == 'LONG':
                    if candle['low'] <= sl:
                        pnl = ((sl - entry) / entry) * 100
                        trades.append({'signal': signal, 'pnl': pnl, 'reason': 'SL'})
                        break
                    elif candle['high'] >= tp:
                        pnl = ((tp - entry) / entry) * 100
                        trades.append({'signal': signal, 'pnl': pnl, 'reason': 'TP'})
                        break
                else:
                    if candle['high'] >= sl:
                        pnl = ((entry - sl) / entry) * 100
                        trades.append({'signal': signal, 'pnl': pnl, 'reason': 'SL'})
                        break
                    elif candle['low'] <= tp:
                        pnl = ((entry - tp) / entry) * 100
                        trades.append({'signal': signal, 'pnl': pnl, 'reason': 'TP'})
                        break
    
    if not trades:
        print("\n❌ 無交易")
        return None
    
    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['pnl'] > 0])
    
    print(f"\n【結果】")
    print(f"交易數: {len(df_trades)}")
    print(f"勝率: {wins/len(df_trades)*100:.1f}%")
    print(f"總盈虧: {df_trades['pnl'].sum():.2f}%")
    print(f"平均: {df_trades['pnl'].mean():.2f}%")
    
    return df_trades


# ========== Part 2: Smart DCA 策略回測 ==========

def backtest_normal_dca(df_weekly, base_weekly=250):
    """普通DCA"""
    total_invested = 0
    total_btc = 0
    
    for idx, row in df_weekly.iterrows():
        price = row['close']
        btc_bought = base_weekly / price
        total_btc += btc_bought
        total_invested += base_weekly
    
    final_value = total_btc * df_weekly.iloc[-1]['close']
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'name': '普通 DCA',
        'invested': total_invested,
        'btc': total_btc,
        'value': final_value,
        'roi': roi
    }


def backtest_smart_dca_a(df_weekly, base_weekly=250):
    """Smart DCA A: RSI調整買入，只買不賣"""
    total_invested = 0
    total_btc = 0
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        
        # RSI調整
        if rsi < 30:
            amount = base_weekly * 2
        elif rsi < 40:
            amount = base_weekly * 1.5
        elif rsi > 70:
            amount = base_weekly * 0.5
        elif rsi > 60:
            amount = base_weekly * 0.75
        else:
            amount = base_weekly
        
        btc_bought = amount / price
        total_btc += btc_bought
        total_invested += amount
    
    final_value = total_btc * df_weekly.iloc[-1]['close']
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'name': 'Smart DCA A (只買)',
        'invested': total_invested,
        'btc': total_btc,
        'value': final_value,
        'roi': roi
    }


def backtest_smart_dca_b(df_weekly, base_weekly=250):
    """Smart DCA B: 買低賣高"""
    total_invested = 0
    total_btc = 0
    reserve_fund = 0
    trades = []
    last_sell_price = 0
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']) or pd.isna(row['ma200']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        ma200 = row['ma200']
        
        # 賣出檢查
        if total_btc > 0:
            # 極端超買賣出
            if rsi > 85 and price > ma200 * 1.5:
                sell_amount = total_btc * 0.4
                sell_value = sell_amount * price
                total_btc -= sell_amount
                reserve_fund += sell_value
                last_sell_price = price
                trades.append({'action': 'SELL', 'price': price, 'amount': sell_amount})
        
        # 買入
        if rsi < 30:
            amount = base_weekly * 2 + reserve_fund * 0.1
        elif rsi < 40:
            amount = base_weekly * 1.6
        elif rsi < 45:
            amount = base_weekly * 1.2
        elif rsi < 65:
            amount = base_weekly
        elif rsi < 75:
            amount = base_weekly * 0.6
        else:
            amount = base_weekly * 0.2
        
        # 買回檢查
        if reserve_fund > 0 and last_sell_price > 0:
            if rsi < 35 and price < last_sell_price * 0.8:
                amount += reserve_fund * 0.3
        
        btc_bought = amount / price
        total_btc += btc_bought
        total_invested += amount
        trades.append({'action': 'BUY', 'price': price, 'amount': btc_bought})
    
    final_value = total_btc * df_weekly.iloc[-1]['close'] + reserve_fund
    
    # 避免除以零
    if total_invested > 0:
        roi = ((final_value / total_invested) - 1) * 100
    else:
        roi = 0
    
    return {
        'name': 'Smart DCA B (買低賣高)',
        'invested': total_invested,
        'btc': total_btc,
        'reserve': reserve_fund,
        'value': final_value,
        'roi': roi,
        'trades': len([t for t in trades if t['action'] == 'SELL'])
    }


def compare_smart_dca():
    """比較Smart DCA策略"""
    print("\n" + "="*70)
    print("Smart DCA 策略回測（2022-2024）")
    print("="*70)
    
    # 載入數據
    df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 週線
    weekly = df.resample('W').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # 指標
    weekly['rsi'] = ta.rsi(weekly['close'], length=14)
    weekly['ma200'] = ta.sma(weekly['close'], length=200)
    weekly.reset_index(inplace=True)
    
    print(f"\n期間: {weekly.iloc[0]['timestamp'].date()} 到 {weekly.iloc[-1]['timestamp'].date()}")
    print(f"週數: {len(weekly)}\n")
    
    # 回測三種策略
    normal = backtest_normal_dca(weekly)
    smart_a = backtest_smart_dca_a(weekly)
    smart_b = backtest_smart_dca_b(weekly)
    
    strategies = [normal, smart_a, smart_b]
    
    for s in strategies:
        print(f"【{s['name']}】")
        print(f"  投入: ${s['invested']:,.0f}")
        print(f"  BTC: {s['btc']:.6f}")
        print(f"  價值: ${s['value']:,.2f}")
        print(f"  報酬: {s['roi']:.2f}%")
        if 'trades' in s:
            print(f"  賣出次數: {s['trades']}")
        print()
    
    # 比較
    print("="*70)
    print("績效比較")
    print("="*70)
    best = max(strategies, key=lambda x: x['roi'])
    print(f"\n✅ 最佳: {best['name']} ({best['roi']:.2f}%)\n")
    
    for s in strategies:
        diff = s['roi'] - normal['roi']
        print(f"   {s['name']}: {s['roi']:.2f}% ({diff:+.2f}%)")


if __name__ == "__main__":
    # 1. Hybrid SFP 熊市回測
    backtest_hybrid_2022()
    
    # 2. Smart DCA 對比
    compare_smart_dca()
