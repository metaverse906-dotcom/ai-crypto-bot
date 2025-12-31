#!/usr/bin/env python3
# tools/advanced_smart_dca.py
"""
Smart DCA 進階策略測試
測試多種改進方案以提升績效
"""

import pandas as pd
import pandas_ta as ta

def load_data():
    """載入數據"""
    df = pd.read_csv('data/backtest/BTC_2021_2024_daily.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    df_weekly = df.resample('W').last().dropna()
    df_weekly['rsi'] = ta.rsi(df_weekly['close'], length=14)
    df_weekly['ma200'] = ta.sma(df_weekly['close'], length=200)
    df_weekly['ma50'] = ta.sma(df_weekly['close'], length=50)
    
    # MACD
    macd = ta.macd(df_weekly['close'])
    if macd is not None:
        df_weekly['macd'] = macd['MACD_12_26_9']
        df_weekly['macd_signal'] = macd['MACDs_12_26_9']
    
    # ADX
    adx_data = ta.adx(df_weekly['high'], df_weekly['low'], df_weekly['close'])
    if adx_data is not None:
        df_weekly['adx'] = adx_data['ADX_14']
    
    return df_weekly


def strategy_baseline(df):
    """基準策略（當前版本）"""
    weekly_cash = 250
    total_cash = 0
    btc = 0
    usdt_reserve = 0
    
    for idx, row in df.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        total_cash += weekly_cash
        
        # 賣出
        if btc > 0 and not pd.isna(row['ma200']):
            if rsi > 75 and price > row['ma200'] * 1.3:
                sell_btc = btc * 0.3
                usdt_reserve += sell_btc * price
                btc -= sell_btc
        
        # 買入
        buy_amount = weekly_cash
        if rsi < 25: buy_amount *= 2.0
        elif rsi < 35: buy_amount *= 1.5
        elif rsi > 75: buy_amount *= 0.7
        
        if usdt_reserve > 0 and rsi < 40:
            extra = min(usdt_reserve * 0.5, weekly_cash)
            buy_amount += extra
            usdt_reserve -= extra
        
        btc += buy_amount / price
    
    final_price = df.iloc[-1]['close']
    total_value = btc * final_price + usdt_reserve
    roi = ((total_value / total_cash) - 1) * 100
    
    return {'name': '基準策略', 'roi': roi, 'btc': btc, 'usdt': usdt_reserve, 'total': total_value}


def strategy_graded_sell(df):
    """改進1：分級賣出策略"""
    weekly_cash = 250
    total_cash = 0
    btc = 0
    usdt_reserve = 0
    
    for idx, row in df.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        total_cash += weekly_cash
        
        # 分級賣出
        if btc > 0 and not pd.isna(row['ma200']):
            ma200 = row['ma200']
            
            if rsi > 80 and price > ma200 * 1.4:
                # 極度超買：賣40%
                sell_btc = btc * 0.4
                usdt_reserve += sell_btc * price
                btc -= sell_btc
            elif rsi > 75 and price > ma200 * 1.3:
                # 超買：賣25%
                sell_btc = btc * 0.25
                usdt_reserve += sell_btc * price
                btc -= sell_btc
            elif rsi > 70 and price > ma200 * 1.2:
                # 偏高：賣15%
                sell_btc = btc * 0.15
                usdt_reserve += sell_btc * price
                btc -= sell_btc
        
        # 買入
        buy_amount = weekly_cash
        if rsi < 25: buy_amount *= 2.0
        elif rsi < 35: buy_amount *= 1.5
        elif rsi > 75: buy_amount *= 0.7
        
        if usdt_reserve > 0 and rsi < 40:
            extra = min(usdt_reserve * 0.5, weekly_cash)
            buy_amount += extra
            usdt_reserve -= extra
        
        btc += buy_amount / price
    
    final_price = df.iloc[-1]['close']
    total_value = btc * final_price + usdt_reserve
    roi = ((total_value / total_cash) - 1) * 100
    
    return {'name': '分級賣出', 'roi': roi, 'btc': btc, 'usdt': usdt_reserve, 'total': total_value}


def strategy_graded_reserve(df):
    """改進2：分級動用儲備"""
    weekly_cash = 250
    total_cash = 0
    btc = 0
    usdt_reserve = 0
    
    for idx, row in df.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        total_cash += weekly_cash
        
        # 賣出
        if btc > 0 and not pd.isna(row['ma200']):
            if rsi > 75 and price > row['ma200'] * 1.3:
                sell_btc = btc * 0.3
                usdt_reserve += sell_btc * price
                btc -= sell_btc
        
        # 買入
        buy_amount = weekly_cash
        if rsi < 25: buy_amount *= 2.0
        elif rsi < 35: buy_amount *= 1.5
        elif rsi > 75: buy_amount *= 0.7
        
        # 分級動用儲備
        if usdt_reserve > 0:
            if rsi < 25:  # 極度超賣
                extra = min(usdt_reserve * 0.8, weekly_cash * 2)
            elif rsi < 30:
                extra = min(usdt_reserve * 0.6, weekly_cash)
            elif rsi < 40:
                extra = min(usdt_reserve * 0.4, weekly_cash * 0.5)
            else:
                extra = 0
            
            buy_amount += extra
            usdt_reserve -= extra
        
        btc += buy_amount / price
    
    final_price = df.iloc[-1]['close']
    total_value = btc * final_price + usdt_reserve
    roi = ((total_value / total_cash) - 1) * 100
    
    return {'name': '分級儲備', 'roi': roi, 'btc': btc, 'usdt': usdt_reserve, 'total': total_value}


def strategy_trend_confirm(df):
    """改進3：趨勢確認賣出"""
    weekly_cash = 250
    total_cash = 0
    btc = 0
    usdt_reserve = 0
    
    for idx, row in df.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        total_cash += weekly_cash
        
        # 趨勢確認賣出
        if btc > 0 and not pd.isna(row['ma200']):
            ma200 = row['ma200']
            ma50_ready = not pd.isna(row['ma50'])
            macd_ready = not pd.isna(row.get('macd'))
            
            sell_signal = False
            
            # 基礎條件
            if rsi > 75 and price > ma200 * 1.3:
                # 加入趨勢確認
                if ma50_ready and price < row['ma50']:
                    # 價格跌破MA50（短期趨勢轉弱）
                    sell_signal = True
                elif macd_ready and row['macd'] < row['macd_signal']:
                    # MACD死叉
                    sell_signal = True
                elif rsi > 80:
                    # RSI極度超買，無需確認
                    sell_signal = True
            
            if sell_signal:
                sell_btc = btc * 0.3
                usdt_reserve += sell_btc * price
                btc -= sell_btc
        
        # 買入
        buy_amount = weekly_cash
        if rsi < 25: buy_amount *= 2.0
        elif rsi < 35: buy_amount *= 1.5
        elif rsi > 75: buy_amount *= 0.7
        
        if usdt_reserve > 0 and rsi < 40:
            extra = min(usdt_reserve * 0.5, weekly_cash)
            buy_amount += extra
            usdt_reserve -= extra
        
        btc += buy_amount / price
    
    final_price = df.iloc[-1]['close']
    total_value = btc * final_price + usdt_reserve
    roi = ((total_value / total_cash) - 1) * 100
    
    return {'name': '趨勢確認', 'roi': roi, 'btc': btc, 'usdt': usdt_reserve, 'total': total_value}


def strategy_combined(df):
    """改進4：組合策略（分級賣出+分級儲備）"""
    weekly_cash = 250
    total_cash = 0
    btc = 0
    usdt_reserve = 0
    
    for idx, row in df.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        total_cash += weekly_cash
        
        # 分級賣出
        if btc > 0 and not pd.isna(row['ma200']):
            ma200 = row['ma200']
            
            if rsi > 80 and price > ma200 * 1.4:
                sell_btc = btc * 0.4
                usdt_reserve += sell_btc * price
                btc -= sell_btc
            elif rsi > 75 and price > ma200 * 1.3:
                sell_btc = btc * 0.25
                usdt_reserve += sell_btc * price
                btc -= sell_btc
            elif rsi > 70 and price > ma200 * 1.2:
                sell_btc = btc * 0.15
                usdt_reserve += sell_btc * price
                btc -= sell_btc
        
        # 買入
        buy_amount = weekly_cash
        if rsi < 25: buy_amount *= 2.0
        elif rsi < 35: buy_amount *= 1.5
        elif rsi > 75: buy_amount *= 0.7
        
        # 分級動用儲備
        if usdt_reserve > 0:
            if rsi < 25:
                extra = min(usdt_reserve * 0.8, weekly_cash * 2)
            elif rsi < 30:
                extra = min(usdt_reserve * 0.6, weekly_cash)
            elif rsi < 40:
                extra = min(usdt_reserve * 0.4, weekly_cash * 0.5)
            else:
                extra = 0
            
            buy_amount += extra
            usdt_reserve -= extra
        
        btc += buy_amount / price
    
    final_price = df.iloc[-1]['close']
    total_value = btc * final_price + usdt_reserve
    roi = ((total_value / total_cash) - 1) * 100
    
    return {'name': '組合策略', 'roi': roi, 'btc': btc, 'usdt': usdt_reserve, 'total': total_value}


def main():
    print("="*70)
    print("Smart DCA 進階策略測試")
    print("="*70)
    
    df = load_data()
    
    print(f"\n期間: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"週數: {len(df)}\n")
    
    # 測試所有策略
    strategies = [
        strategy_baseline,
        strategy_graded_sell,
        strategy_graded_reserve,
        strategy_trend_confirm,
        strategy_combined
    ]
    
    results = []
    for strategy in strategies:
        result = strategy(df)
        results.append(result)
        print(f"【{result['name']}】")
        print(f"  報酬率: {result['roi']:.2f}%")
        print(f"  BTC: {result['btc']:.6f}")
        print(f"  USDT: ${result['usdt']:,.2f}")
        print(f"  總資產: ${result['total']:,.2f}\n")
    
    # 比較
    print("="*70)
    print("績效比較")
    print("="*70)
    
    baseline_roi = results[0]['roi']
    for r in results:
        diff = r['roi'] - baseline_roi
        if diff > 0:
            print(f"✅ {r['name']}: {r['roi']:.2f}% ({diff:+.2f}%)")
        elif diff == 0:
            print(f"⚪ {r['name']}: {r['roi']:.2f}% (基準)")
        else:
            print(f"❌ {r['name']}: {r['roi']:.2f}% ({diff:+.2f}%)")
    
    # 找出最佳
    best = max(results, key=lambda x: x['roi'])
    if best['roi'] > baseline_roi:
        print(f"\n🎉 最佳策略：{best['name']}")
        print(f"   改善：{best['roi'] - baseline_roi:+.2f}%")

if __name__ == "__main__":
    main()
