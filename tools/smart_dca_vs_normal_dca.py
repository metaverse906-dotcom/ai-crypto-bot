#!/usr/bin/env python3
# tools/smart_dca_vs_normal_dca.py
"""
智能 DCA vs 普通 DCA 比較
智能 DCA：使用 RSI 調整買入金額
"""

import pandas as pd
import pandas_ta as ta

def normal_dca():
    """普通 DCA：每月固定 $1000"""
    df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 每月 1 號
    monthly = df.resample('MS').first()
    
    monthly_investment = 1000
    total_invested = 0
    total_btc = 0
    
    for date, row in monthly.iterrows():
        price = row['close']
        btc_bought = monthly_investment / price
        total_btc += btc_bought
        total_invested += monthly_investment
    
    final_price = monthly.iloc[-1]['close']
    final_value = total_btc * final_price
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'name': '普通 DCA',
        'invested': total_invested,
        'btc': total_btc,
        'value': final_value,
        'roi': roi,
        'trades': len(monthly)
    }


def smart_dca_rsi():
    """智能 DCA：RSI < 30 買更多，RSI > 70 買更少"""
    df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 計算日線 RSI
    df.set_index('timestamp', inplace=True)
    daily = df.resample('D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # RSI
    daily['rsi'] = ta.rsi(daily['close'], length=14)
    
    # 每月 1 號
    monthly = daily.resample('MS').first()
    
    base_investment = 1000
    total_invested = 0
    total_btc = 0
    
    trades = []
    
    for date, row in monthly.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        
        # 根據 RSI 調整投入金額
        if rsi < 30:
            # 超賣：加倍投入
            investment = base_investment * 2
            signal = '超賣(加倍)'
        elif rsi < 40:
            # 偏低：1.5倍
            investment = base_investment * 1.5
            signal = '偏低(1.5x)'
        elif rsi > 70:
            # 超買：減半
            investment = base_investment * 0.5
            signal = '超買(減半)'
        elif rsi > 60:
            # 偏高：0.75倍
            investment = base_investment * 0.75
            signal = '偏高(0.75x)'
        else:
            # 中性：正常
            investment = base_investment
            signal = '中性'
        
        btc_bought = investment / price
        total_btc += btc_bought
        total_invested += investment
        
        trades.append({
            'date': date,
            'price': price,
            'rsi': rsi,
            'investment': investment,
            'signal': signal,
            'btc': btc_bought
        })
    
    final_price = monthly.iloc[-1]['close']
    final_value = total_btc * final_price
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'name': '智能 DCA (RSI)',
        'invested': total_invested,
        'btc': total_btc,
        'value': final_value,
        'roi': roi,
        'trades': len(trades),
        'details': trades
    }


def smart_dca_ma():
    """智能 DCA：價格低於 MA200 買更多"""
    df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 日線
    daily = df.resample('D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # MA 200
    daily['ma200'] = ta.sma(daily['close'], length=200)
    
    monthly = daily.resample('MS').first()
    
    base_investment = 1000
    total_invested = 0
    total_btc = 0
    
    for date, row in monthly.iterrows():
        if pd.isna(row['ma200']):
            continue
        
        price = row['close']
        ma200 = row['ma200']
        
        # 根據與 MA200 的距離調整
        distance = ((price - ma200) / ma200) * 100
        
        if distance < -20:
            # 遠低於 MA200：加倍
            investment = base_investment * 2
        elif distance < -10:
            investment = base_investment * 1.5
        elif distance > 20:
            # 遠高於 MA200：減半
            investment = base_investment * 0.5
        elif distance > 10:
            investment = base_investment * 0.75
        else:
            investment = base_investment
        
        btc_bought = investment / price
        total_btc += btc_bought
        total_invested += investment
    
    final_price = monthly.iloc[-1]['close']
    final_value = total_btc * final_price
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'name': '智能 DCA (MA200)',
        'invested': total_invested,
        'btc': total_btc,
        'value': final_value,
        'roi': roi,
        'trades': len(monthly) - 200//30  # 扣除 MA200 計算期
    }


def compare_all():
    """比較所有策略"""
    print("="*70)
    print("DCA 策略比較")
    print("="*70)
    
    # 執行三種策略
    normal = normal_dca()
    smart_rsi = smart_dca_rsi()
    smart_ma = smart_dca_ma()
    
    strategies = [normal, smart_rsi, smart_ma]
    
    print(f"\n期間：2023-2024（約 24 個月）\n")
    
    for s in strategies:
        print(f"【{s['name']}】")
        print(f"  總投入: ${s['invested']:,.0f}")
        print(f"  購買 BTC: {s['btc']:.6f}")
        print(f"  最終價值: ${s['value']:,.2f}")
        print(f"  報酬率: {s['roi']:.2f}%")
        print(f"  交易次數: {s['trades']}")
        print()
    
    # 找出最佳策略
    best = max(strategies, key=lambda x: x['roi'])
    
    print("="*70)
    print("比較結果")
    print("="*70)
    
    for s in strategies:
        diff = s['roi'] - normal['roi']
        symbol = '✅' if s == best else '⭐' if diff > 0 else '⚪'
        print(f"{symbol} {s['name']}: {s['roi']:.2f}% ({diff:+.2f}%)")
    
    print(f"\n最佳策略: {best['name']}")
    print(f"優於普通 DCA: {best['roi'] - normal['roi']:.2f}%")
    
    # 顯示智能 DCA 的詳細操作
    if 'details' in smart_rsi:
        print(f"\n{'='*70}")
        print("智能 DCA (RSI) 操作記錄（前 10 筆）")
        print(f"{'='*70}")
        for trade in smart_rsi['details'][:10]:
            print(f"{trade['date'].strftime('%Y-%m')} | "
                  f"RSI:{trade['rsi']:.1f} | "
                  f"${trade['investment']:,.0f} | "
                  f"{trade['signal']}")


if __name__ == "__main__":
    compare_all()
