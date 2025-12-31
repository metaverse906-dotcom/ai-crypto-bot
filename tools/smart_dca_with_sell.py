#!/usr/bin/env python3
# tools/smart_dca_with_sell.py
"""
完整Smart DCA：買低賣高版本
包含賣出邏輯和USDT儲備管理
"""

import pandas as pd
import pandas_ta as ta

def normal_dca_baseline(df_weekly):
    """普通DCA基準"""
    invested = 0
    btc = 0
    
    for idx, row in df_weekly.iterrows():
        price = row['close']
        invested += 250
        btc += 250 / price
    
    final_price = df_weekly.iloc[-1]['close']
    total_value = btc * final_price
    roi = ((total_value / invested) - 1) * 100
    
    return {
        'name': '普通 DCA',
        'invested': invested,
        'btc': btc,
        'usdt': 0,
        'total_value': total_value,
        'roi': roi
    }


def smart_dca_buy_only(df_weekly):
    """Smart DCA：只調整買入"""
    invested = 0
    btc = 0
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        
        if rsi < 25:
            amount = 500
        elif rsi < 35:
            amount = 325
        elif rsi > 80:
            amount = 175
        elif rsi > 75:
            amount = 212
        else:
            amount = 250
        
        invested += amount
        btc += amount / price
    
    final_price = df_weekly.iloc[-1]['close']
    total_value = btc * final_price
    roi = ((total_value / invested) - 1) * 100
    
    return {
        'name': 'Smart DCA (只買)',
        'invested': invested,
        'btc': btc,
        'usdt': 0,
        'total_value': total_value,
        'roi': roi
    }


def smart_dca_with_sell(df_weekly):
    """Smart DCA：買低賣高完整版"""
    weekly_budget = 250  # 每週固定預算
    total_invested = 0   # 總投入（累計預算）
    btc = 0              # BTC持倉
    usdt_reserve = 0     # USDT儲備（賣出所得）
    
    trades = []
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']) or pd.isna(row['ma200']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        ma200 = row['ma200']
        
        # 每週累加預算
        total_invested += weekly_budget
        
        # === 賣出邏輯 ===
        if btc > 0:
            # 極端超買且遠高於MA200
            if rsi > 85 and price > ma200 * 1.6:
                # 賣出40% BTC
                sell_btc = btc * 0.4
                sell_value = sell_btc * price
                btc -= sell_btc
                usdt_reserve += sell_value
                trades.append({
                    'week': idx,
                    'action': 'SELL',
                    'btc': sell_btc,
                    'price': price,
                    'value': sell_value,
                    'rsi': rsi
                })
        
        # === 買入邏輯 ===
        # 基礎買入金額（本週預算）
        buy_amount = weekly_budget
        
        # RSI調整
        if rsi < 25:
            buy_amount = weekly_budget * 2
        elif rsi < 35:
            buy_amount = weekly_budget * 1.5
        elif rsi > 75:
            buy_amount = weekly_budget * 0.7
        
        # 如果有儲備且RSI<35，動用儲備加碼
        if usdt_reserve > 0 and rsi < 35:
            extra_buy = min(usdt_reserve * 0.3, weekly_budget)
            buy_amount += extra_buy
            usdt_reserve -= extra_buy
        
        # 執行買入
        btc_bought = buy_amount / price
        btc += btc_bought
        
        if buy_amount != weekly_budget:
            trades.append({
                'week': idx,
                'action': 'BUY',
                'btc': btc_bought,
                'price': price,
                'amount': buy_amount,
                'rsi': rsi
            })
    
    # 最終總資產 = BTC價值 + USDT儲備
    final_price = df_weekly.iloc[-1]['close']
    btc_value = btc * final_price
    total_value = btc_value + usdt_reserve
    
    # ROI應該基於總投入現金
    roi = ((total_value / total_cash_added) - 1) * 100
    
    sell_count = len([t for t in trades if t['action'] == 'SELL'])
    
    return {
        'name': 'Smart DCA (買低賣高)',
        'cash_added': total_cash_added,  # 實際投入現金
        'spent': total_spent,  # 實際花費
        'invested': total_cash_added,  # 用於ROI計算
        'btc': btc,
        'usdt': usdt_reserve,
        'btc_value': btc_value,
        'total_value': total_value,
        'roi': roi,
        'sell_trades': sell_count,
        'trades': trades
    }


def main():
    # 載入數據
    df = pd.read_csv('data/backtest/BTC_2021_2024_daily.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # 週線
    df_weekly = df.resample('W').last().dropna()
    df_weekly['rsi'] = ta.rsi(df_weekly['close'], length=14)
    df_weekly['ma200'] = ta.sma(df_weekly['close'], length=200)
    
    print("="*70)
    print("Smart DCA 完整測試：買低賣高版本")
    print("="*70)
    print(f"期間: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"週數: {len(df_weekly)}\n")
    
    # 測試三種策略
    normal = normal_dca_baseline(df_weekly)
    smart_buy = smart_dca_buy_only(df_weekly)
    smart_sell = smart_dca_with_sell(df_weekly)
    
    results = [normal, smart_buy, smart_sell]
    
    for r in results:
        print(f"【{r['name']}】")
        print(f"  總投入: ${r['invested']:,.0f}")
        print(f"  BTC: {r['btc']:.6f}")
        if 'usdt' in r and r['usdt'] > 0:
            print(f"  USDT儲備: ${r['usdt']:,.2f}")
        if 'btc_value' in r:
            print(f"  BTC價值: ${r['btc_value']:,.2f}")
        print(f"  總資產: ${r['total_value']:,.2f}")
        print(f"  報酬率: {r['roi']:.2f}%")
        if 'sell_trades' in r:
            print(f"  賣出次數: {r['sell_trades']}")
        print()
    
    # 比較
    print("="*70)
    print("績效比較")
    print("="*70)
    
    diff_buy = smart_buy['roi'] - normal['roi']
    diff_sell = smart_sell['roi'] - normal['roi']
    
    print(f"Smart (只買) vs 普通: {diff_buy:+.2f}%")
    print(f"Smart (買低賣高) vs 普通: {diff_sell:+.2f}%")
    print(f"\n買低賣高 vs 只買: {diff_sell - diff_buy:+.2f}%")
    
    # 顯示賣出記錄
    if 'trades' in smart_sell and smart_sell['sell_trades'] > 0:
        print(f"\n{'='*70}")
        print("賣出記錄")
        print(f"{'='*70}")
        for t in smart_sell['trades']:
            if t['action'] == 'SELL':
                print(f"{t['week'].date()} | 賣出 {t['btc']:.6f} BTC @ ${t['price']:,.0f} | "
                      f"獲得 ${t['value']:,.0f} | RSI:{t['rsi']:.1f}")

if __name__ == "__main__":
    main()
