#!/usr/bin/env python3
# tools/compare_with_dca.py
"""
Hybrid SFP vs DCA BTC 績效比較
"""

import pandas as pd
import numpy as np

def calculate_dca_btc():
    """計算 DCA BTC 績效"""
    # 載入數據
    df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 轉換為月度數據（每月1號投資）
    df.set_index('timestamp', inplace=True)
    monthly = df.resample('MS').first()  # MS = Month Start
    
    print("="*70)
    print("DCA BTC 績效計算")
    print("="*70)
    print(f"\n期間: {monthly.index[0]} 到 {monthly.index[-1]}")
    print(f"月數: {len(monthly)}")
    
    # DCA 策略：每月投入 $1000
    monthly_investment = 1000
    total_invested = 0
    total_btc = 0
    
    trades = []
    for date, row in monthly.iterrows():
        price = row['close']
        btc_bought = monthly_investment / price
        total_btc += btc_bought
        total_invested += monthly_investment
        
        trades.append({
            'date': date,
            'price': price,
            'btc_bought': btc_bought,
            'total_btc': total_btc,
            'total_invested': total_invested,
            'current_value': total_btc * price
        })
    
    df_trades = pd.DataFrame(trades)
    
    # 最終價值
    final_price = monthly.iloc[-1]['close']
    final_value = total_btc * final_price
    profit = final_value - total_invested
    roi = (profit / total_invested) * 100
    
    print(f"\n【DCA 結果】")
    print(f"總投入: ${total_invested:,.0f}")
    print(f"購買 BTC: {total_btc:.4f}")
    print(f"平均成本: ${total_invested/total_btc:,.2f}")
    print(f"最終價值: ${final_value:,.2f}")
    print(f"獲利: ${profit:,.2f}")
    print(f"報酬率: {roi:.2f}%")
    
    # 計算年化報酬
    years = len(monthly) / 12
    annual_roi = ((final_value / total_invested) ** (1/years) - 1) * 100
    print(f"年化報酬: {annual_roi:.2f}%")
    
    return {
        'total_invested': total_invested,
        'final_value': final_value,
        'roi': roi,
        'annual_roi': annual_roi,
        'trades': len(monthly)
    }


def compare_strategies():
    """比較策略"""
    print("\n" + "="*70)
    print("策略比較")
    print("="*70)
    
    # DCA 績效
    dca = calculate_dca_btc()
    
    # Hybrid SFP 績效（從回測已知）
    hybrid = {
        'total_invested': 1000,  # 初始資金
        'final_value': 1000 * (1 + 218.81/100),  # +218.81%
        'roi': 218.81,
        'trades': 251,
        'win_rate': 37.8,
        'period': '2023-2024 (約2年)'
    }
    
    print(f"\n【Hybrid SFP】")
    print(f"初始資金: ${hybrid['total_invested']:,.0f}")
    print(f"最終價值: ${hybrid['final_value']:,.2f}")
    print(f"報酬率: {hybrid['roi']:.2f}%")
    print(f"交易次數: {hybrid['trades']}")
    print(f"勝率: {hybrid['win_rate']}%")
    
    print(f"\n{'='*70}")
    print("對比分析")
    print(f"{'='*70}")
    
    # 同等資金比較（都投入 DCA 的總金額）
    hybrid_scaled = {
        'invested': dca['total_invested'],
        'final': dca['total_invested'] * (1 + hybrid['roi']/100),
        'roi': hybrid['roi']
    }
    
    print(f"\n假設投入同等資金 ${dca['total_invested']:,.0f}:")
    print(f"\nDCA BTC:")
    print(f"  最終價值: ${dca['final_value']:,.2f}")
    print(f"  報酬率: {dca['roi']:.2f}%")
    print(f"  年化報酬: {dca['annual_roi']:.2f}%")
    print(f"  投資次數: {dca['trades']}")
    
    print(f"\nHybrid SFP:")
    print(f"  最終價值: ${hybrid_scaled['final']:,.2f}")
    print(f"  報酬率: {hybrid_scaled['roi']:.2f}%")
    print(f"  交易次數: {hybrid['trades']}")
    
    # 差異
    diff_value = hybrid_scaled['final'] - dca['final_value']
    diff_roi = hybrid_scaled['roi'] - dca['roi']
    
    print(f"\n{'='*70}")
    print("績效差異")
    print(f"{'='*70}")
    print(f"價值差異: ${diff_value:,.2f}")
    print(f"報酬差異: {diff_roi:+.2f}%")
    
    if diff_roi > 0:
        print(f"\n✅ Hybrid SFP 優於 DCA {diff_roi:.2f}%")
        print(f"   相當於多賺 ${diff_value:,.2f}")
    else:
        print(f"\n❌ Hybrid SFP 劣於 DCA {abs(diff_roi):.2f}%")
        print(f"   相當於少賺 ${abs(diff_value):,.2f}")
    
    print(f"\n{'='*70}")


if __name__ == "__main__":
    compare_strategies()
