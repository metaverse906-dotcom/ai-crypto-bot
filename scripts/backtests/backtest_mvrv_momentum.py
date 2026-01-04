#!/usr/bin/env python3
# scripts/backtests/backtest_mvrv_momentum.py
"""
MVRV ?•èƒ½è³?‡ºç­–ç•¥?æ¸¬

?©ç¨®?ˆæœ¬ï¼?
1. ç´?MVRV ?•èƒ½ç­–ç•¥
2. MVRV ?•èƒ½ + ?Ÿç??¥ç???
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

INITIAL_CAPITAL = 10000
WEEKLY_INVESTMENT = 250
CORE_RATIO = 0.4
TRADE_FEE = 0.001

def fetch_data():
    """?²å??¸æ?"""
    print("?“¥ ?²å? 2020-2025 ?¸æ?...")
    
    exchange = ccxt.binance()
    start_date = datetime(2020, 1, 1)
    since = int(start_date.timestamp() * 1000)
    
    all_ohlcv = []
    current = since
    
    while current < int(datetime.now().timestamp() * 1000):
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=current, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        current = ohlcv[-1][0] + 86400000
        if len(ohlcv) < 1000:
            break
    
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['price'] = df['close']
    
    return df[['date', 'price']]

def calculate_indicators(df):
    """è¨ˆç??€?‰æ?æ¨?""
    # RSI
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ?ˆç? RSI
    gain_30 = (delta.where(delta > 0, 0)).rolling(window=30).mean()
    loss_30 = (-delta.where(delta < 0, 0)).rolling(window=30).mean()
    rs_30 = gain_30 / loss_30
    df['rsi_monthly'] = 100 - (100 / (1 + rs_30))
    
    # 200??MA
    df['ma_200w'] = df['price'].rolling(window=1400).mean()
    
    # MVRV ä»??
    df['mvrv'] = df['price'] / df['ma_200w']
    
    # MVRV ?•èƒ½?‡æ?
    # 1. 7?¥è??–ç?
    df['mvrv_7d_change'] = df['mvrv'].pct_change(7) * 100
    
    # 2. 14?¥è??–ç?
    df['mvrv_14d_change'] = df['mvrv'].pct_change(14) * 100
    
    # 3. ? é€Ÿåº¦ï¼ˆè??–ç??„è??–ï?
    df['mvrv_acceleration'] = df['mvrv_7d_change'].diff(7)
    
    # 4. MVRV å¾é?é»å???
    df['mvrv_high'] = df['mvrv'].rolling(window=30).max()
    df['mvrv_drawdown'] = (df['mvrv'] - df['mvrv_high']) / df['mvrv_high'] * 100
    
    # ATH
    df['ath'] = df['price'].expanding().max()
    
    # F&G æ¨¡æ“¬
    df['price_change_30d'] = df['price'].pct_change(30) * 100
    df['fg'] = 50 + df['price_change_30d'].clip(-50, 50)
    
    return df

def get_buy_multiplier(mvrv, rsi, fg, price, ath):
    """è²·å…¥?æ•¸ï¼ˆå??è¼¯ï¼?""
    if mvrv < 0.1:
        mvrv_score = 0
    elif mvrv < 1.0:
        mvrv_score = 10
    elif mvrv < 3.0:
        mvrv_score = 30
    elif mvrv < 5.0:
        mvrv_score = 50
    else:
        mvrv_score = 80
    
    rsi_score = rsi if not pd.isna(rsi) else 50
    fg_score = fg if not pd.isna(fg) else 50
    
    composite = (mvrv_score * 0.65) + (rsi_score * 0.25) + (fg_score * 0.10)
    
    if composite < 15:
        multiplier = 3.5
    elif composite < 25:
        multiplier = 2.0
    elif composite < 35:
        multiplier = 1.5
    elif composite < 50:
        multiplier = 1.0
    elif composite < 60:
        multiplier = 0.5
    else:
        multiplier = 0.0
    
    # ?›å?èª¿æ•´
    if price > ath * 1.2:
        multiplier *= 0.5
    if price > ath * 1.5:
        multiplier = 0.0
    
    return multiplier

def check_mvrv_momentum_sell(row, peak_mvrv, mvrv_sell_triggered):
    """
    æª¢æ¸¬ MVRV ?•èƒ½è³?‡ºä¿¡è?
    
    ä¸‰é?æ®µæª¢æ¸¬ï?
    1. è­¦å?ï¼šMVRV å¢é€Ÿæ?ç·?
    2. ?Ÿå?ï¼šMVRV ?”é?ä½ä?æ¸›é€?
    3. ç¢ºè?ï¼šMVRV ?‹å?ä¸‹é?
    """
    if pd.isna(row['mvrv']) or pd.isna(row['mvrv_acceleration']):
        return None, peak_mvrv
    
    # ?´æ–°å³°å€?
    current_mvrv = row['mvrv']
    if current_mvrv > peak_mvrv:
        peak_mvrv = current_mvrv
    
    # ?æ®µ 1ï¼šMVRV > 2.0 ä¸”å??Ÿåº¦è½‰è?ï¼ˆæ??Ÿï?
    if current_mvrv > 2.0 and row['mvrv_acceleration'] < -0.5 and 'stage1' not in mvrv_sell_triggered:
        return {
            'stage': 1,
            'pct': 0.10,
            'reason': f'MVRV æ¸›é€?(MVRV={current_mvrv:.2f}, ? é€Ÿåº¦={row["mvrv_acceleration"]:.2f})'
        }, peak_mvrv
    
    # ?æ®µ 2ï¼šMVRV > 2.5 ä¸?14?¥è??–ç? < 0ï¼ˆé?å§‹ä??ï?
    if current_mvrv > 2.5 and row['mvrv_14d_change'] < 0 and 'stage2' not in mvrv_sell_triggered:
        return {
            'stage': 2,
            'pct': 0.20,
            'reason': f'MVRV è½‰å?ä¸‹é? (MVRV={current_mvrv:.2f}, 14dè®Šå?={row["mvrv_14d_change"]:.2f}%)'
        }, peak_mvrv
    
    # ?æ®µ 3ï¼šMVRV å¾é?é»å???> 15%
    if row['mvrv_drawdown'] < -15 and 'stage3' not in mvrv_sell_triggered:
        return {
            'stage': 3,
            'pct': 0.70,
            'reason': f'MVRV å¤§å??æ’¤ ({row["mvrv_drawdown"]:.1f}% from peak {peak_mvrv:.2f})'
        }, peak_mvrv
    
    return None, peak_mvrv

def backtest_pure_momentum(df):
    """ç´?MVRV ?•èƒ½ç­–ç•¥"""
    print("\n?? ?æ¸¬ï¼šç? MVRV ?•èƒ½ç­–ç•¥")
    print("="*70)
    
    core_btc = 0.0
    trade_btc = 0.0
    cash = INITIAL_CAPITAL
    
    trades = []
    peak_mvrv = 0
    mvrv_sell_triggered = set()
    
    for i in range(1400, len(df), 7):
        row = df.iloc[i]
        
        if pd.isna(row['mvrv']) or pd.isna(row['rsi']):
            continue
        
        # è²·å…¥
        multiplier = get_buy_multiplier(row['mvrv'], row['rsi'], row['fg'], row['price'], row['ath'])
        invest_amount = WEEKLY_INVESTMENT * multiplier
        
        if cash >= invest_amount and invest_amount > 0:
            btc_bought = (invest_amount * (1 - TRADE_FEE)) / row['price']
            core_btc += btc_bought * CORE_RATIO
            trade_btc += btc_bought * (1 - CORE_RATIO)
            cash -= invest_amount
            
            trades.append({
                'date': row['date'],
                'type': 'BUY',
                'price': row['price'],
                'amount': btc_bought,
                'usd': invest_amount
            })
        
        # è³?‡ºï¼ˆMVRV ?•èƒ½ï¼?
        if trade_btc > 0:
            sell_signal, peak_mvrv = check_mvrv_momentum_sell(row, peak_mvrv, mvrv_sell_triggered)
            
            if sell_signal:
                stage_key = f'stage{sell_signal["stage"]}'
                if stage_key not in mvrv_sell_triggered:
                    sell_amount = trade_btc * sell_signal['pct']
                    sell_value = sell_amount * row['price'] * (1 - TRADE_FEE)
                    
                    cash += sell_value
                    trade_btc -= sell_amount
                    mvrv_sell_triggered.add(stage_key)
                    
                    trades.append({
                        'date': row['date'],
                        'type': 'SELL',
                        'price': row['price'],
                        'amount': sell_amount,
                        'usd': sell_value,
                        'reason': sell_signal['reason']
                    })
    
    current_price = df.iloc[-1]['price']
    total_value = (core_btc + trade_btc) * current_price + cash
    
    return total_value, trades, core_btc, trade_btc, cash

def backtest_combined(df):
    """MVRV ?•èƒ½ + ?Ÿç??¥ç???""
    print("\n?? ?æ¸¬ï¼šMVRV ?•èƒ½ + ?Ÿç??¥ç???)
    print("="*70)
    
    core_btc = 0.0
    trade_btc = 0.0
    cash = INITIAL_CAPITAL
    
    trades = []
    peak_mvrv = 0
    peak_price = 0
    sell_triggered = set()
    
    for i in range(1400, len(df), 7):
        row = df.iloc[i]
        
        if pd.isna(row['mvrv']) or pd.isna(row['rsi']):
            continue
        
        # ?´æ–°å³°å€?
        if row['price'] > peak_price:
            peak_price = row['price']
        
        # è²·å…¥
        multiplier = get_buy_multiplier(row['mvrv'], row['rsi'], row['fg'], row['price'], row['ath'])
        invest_amount = WEEKLY_INVESTMENT * multiplier
        
        if cash >= invest_amount and invest_amount > 0:
            btc_bought = (invest_amount * (1 - TRADE_FEE)) / row['price']
            core_btc += btc_bought * CORE_RATIO
            trade_btc += btc_bought * (1 - CORE_RATIO)
            cash -= invest_amount
            
            trades.append({
                'date': row['date'],
                'type': 'BUY',
                'price': row['price'],
                'amount': btc_bought,
                'usd': invest_amount
            })
        
        # è³?‡ºï¼ˆå??è§¸?¼ï?
        if trade_btc > 0:
            sell_reason = None
            sell_pct = 0
            trigger_key = None
            
            # 1. MVRV ?•èƒ½ï¼ˆå„ª?ˆç??€é«˜ï?
            momentum_signal, peak_mvrv = check_mvrv_momentum_sell(row, peak_mvrv, sell_triggered)
            if momentum_signal:
                trigger_key = f'momentum_stage{momentum_signal["stage"]}'
                if trigger_key not in sell_triggered:
                    sell_pct = momentum_signal['pct']
                    sell_reason = f'MVRV ?•èƒ½: {momentum_signal["reason"]}'
            
            # 2. RSI > 80
            elif row['rsi_monthly'] > 80 and 'rsi_80' not in sell_triggered:
                sell_pct = 0.10
                sell_reason = f'?ˆç? RSI > 80 ({row["rsi_monthly"]:.1f})'
                trigger_key = 'rsi_80'
            
            # 3. ?èª¿ > 20%
            elif peak_price > 0:
                drawdown = (row['price'] - peak_price) / peak_price
                if drawdown < -0.20 and 'drawdown_20' not in sell_triggered:
                    sell_pct = 0.30
                    sell_reason = f'?èª¿ {drawdown*100:.1f}% (from ${peak_price:,.0f})'
                    trigger_key = 'drawdown_20'
            
            # ?·è?è³?‡º
            if sell_pct > 0 and trigger_key:
                sell_amount = trade_btc * sell_pct
                sell_value = sell_amount * row['price'] * (1 - TRADE_FEE)
                
                cash += sell_value
                trade_btc -= sell_amount
                sell_triggered.add(trigger_key)
                
                trades.append({
                    'date': row['date'],
                    'type': 'SELL',
                    'price': row['price'],
                    'amount': sell_amount,
                    'usd': sell_value,
                    'reason': sell_reason
                })
    
    current_price = df.iloc[-1]['price']
    total_value = (core_btc + trade_btc) * current_price + cash
    
    return total_value, trades, core_btc, trade_btc, cash

def main():
    """ä¸»å‡½??""
    print("="*70)
    print("?? MVRV ?•èƒ½è³?‡ºç­–ç•¥?æ¸¬ï¼?020-2025ï¼?)
    print("="*70)
    
    df = fetch_data()
    df = calculate_indicators(df)
    
     print(f"\\n?¸æ?ç¯„å?ï¼š{df.iloc[1400]['date'].date()} ~ {df.iloc[-1]['date'].date()}")
    
    # ?æ¸¬?©ç¨®ç­–ç•¥
    value_momentum, trades_momentum, core_m, trade_m, cash_m = backtest_pure_momentum(df)
    value_combined, trades_combined, core_c, trade_c, cash_c = backtest_combined(df)
    
    # HODL å°æ?
    hodl_btc = INITIAL_CAPITAL / df.iloc[1400]['price']
    current_price = df.iloc[-1]['price']
    hodl_value = hodl_btc * current_price
    
    # ?Ÿç³»çµ?
    original_value = 17310
    
    # çµæ?å°æ?
     print(f"\\n{'='*70}")
    print("?? ç­–ç•¥ç¸¾æ?å°æ?")
    print(f"{'='*70}\n")
    
    print(f"{'ç­–ç•¥':<20} {'ç¸½åƒ¹??:>12} {'ROI':>8} {'vs HODL':>10} {'è³?‡ºæ¬¡æ•¸':>8}")
    print("-"*70)
    print(f"{'?Ÿç³»çµ?:<20} ${original_value:>11,.0f} {(original_value-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>7.1f}% "
          f"{(original_value-hodl_value)/hodl_value*100:>9.1f}% {'2':>8}")
    print(f"{'ç´?MVRV ?•èƒ½':<20} ${value_momentum:>11,.0f} {(value_momentum-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>7.1f}% "
          f"{(value_momentum-hodl_value)/hodl_value*100:>9.1f}% {len([t for t in trades_momentum if t['type']=='SELL']):>8}")
    print(f"{'MVRV?•èƒ½+?Ÿç???:<20} ${value_combined:>11,.0f} {(value_combined-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>7.1f}% "
          f"{(value_combined-hodl_value)/hodl_value*100:>9.1f}% {len([t for t in trades_combined if t['type']=='SELL']):>8}")
    print(f"{'HODL':<20} ${hodl_value:>11,.0f} {(hodl_value-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:>7.1f}% {'0.0%':>10} {'0':>8}")
    
    # è³?‡ºè¨˜é?
    print(f"\\n{'='*70}")
    print("?? è³?‡ºè¨˜é?")
    print(f"{'='*70}")
    
     print(f"\\nç´?MVRV ?•èƒ½ç­–ç•¥ï¼?)
    sell_m = [t for t in trades_momentum if t['type'] == 'SELL']
    if sell_m:
        for t in sell_m:
            print(f"  {t['date'].date()} | ${t['price']:>7,.0f} | {t['amount']:.6f} BTC ??${t['usd']:>10,.0f}")
            print(f"    {t['reason']}")
    else:
        print("  ? ï? ?ªè§¸?¼è³£??)
    
     print(f"\\nMVRV ?•èƒ½ + ?Ÿç??¥ç??ˆï?")
    sell_c = [t for t in trades_combined if t['type'] == 'SELL']
    if sell_c:
        for t in sell_c:
            print(f"  {t['date'].date()} | ${t['price']:>7,.0f} | {t['amount']:.6f} BTC ??${t['usd']:>10,.0f}")
            print(f"    {t['reason']}")
    else:
        print("  ? ï? ?ªè§¸?¼è³£??)
    
     print(f"\\n???æ¸¬å®Œæ?")

if __name__ == "__main__":
    main()
