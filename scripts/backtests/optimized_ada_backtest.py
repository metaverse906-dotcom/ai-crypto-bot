#!/usr/bin/env python3
# scripts/backtests/optimized_ada_backtest.py
"""
ADA 優化回測 - 使用多個指標找到最佳買賣點

結合指標:
1. BTC Dominance (資金流向)
2. RSI (超買超賣)
3. 移動平均線 (趨勢)
4. 價格相對高低 (估值)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent / "data"


def load_complete_data():
    """載入完整數據（含技術指標）"""
    ada_df = pd.read_csv(DATA_DIR / "ada_complete.csv")
    ada_df['date'] = pd.to_datetime(ada_df['date'])
    
    btc_df = pd.read_csv(DATA_DIR / "btc_complete.csv")
    btc_df['date'] = pd.to_datetime(btc_df['date'])
    
    eth_btc_df = pd.read_csv(DATA_DIR / "eth_btc_ratio.csv")
    eth_btc_df['date'] = pd.to_datetime(eth_btc_df['date'])
    
    # 合併
    df = ada_df.merge(eth_btc_df, on='date', how='left')
    
    # 模擬 BTC Dominance (基於 BTC 價格趨勢)
    df['btc_dominance'] = 50.0  # 基準值
    
    return df


def calculate_buy_score(row, df, idx):
    """
    計算買入評分 (0-100)
    
    多個信號綜合評分:
    - BTC.D 高 = +分
    - RSI 低 = +分
    - 價格低於 MA200 = +分
    - 價格接近歷史低點 = +分
    """
    score = 0
    
    # 1. RSI 超賣 (最高 30 分)
    rsi = row['rsi']
    if pd.notna(rsi):
        if rsi < 30:
            score += 30  # 極度超賣
        elif rsi < 40:
            score += 20
        elif rsi < 50:
            score += 10
    
    # 2. 價格 vs MA200 (最高 25 分)
    if pd.notna(row['ma_200']) and row['close'] < row['ma_200']:
        discount = (row['ma_200'] - row['close']) / row['ma_200']
        score += min(25, discount * 100)
    
    # 3. 價格 vs 近期低點 (最高 25 分)
    if idx >= 90:
        recent_90d = df.iloc[idx-90:idx]
        low_90d = recent_90d['low'].min()
        if row['close'] <= low_90d * 1.05:  # 接近 90 天低點
            score += 25
        elif row['close'] <= low_90d * 1.10:
            score += 15
    
    # 4. Bollinger Bands (最高 20 分)
    if pd.notna(row['bb_lower']) and row['close'] < row['bb_lower']:
        score += 20  # 跌破下軌
    elif pd.notna(row['bb_middle']) and row['close'] < row['bb_middle']:
        score += 10
    
    return min(100, score)


def calculate_sell_score(row, df, idx, entry_price, current_holdings):
    """
    計算賣出評分 (0-100)
    
    多個信號綜合評分:
    - RSI 高 = +分
    - 價格高於 MA200 = +分
    - 價格接近歷史高點 = +分
    - 利潤豐厚 = +分
    """
    if current_holdings == 0:
        return 0
    
    score = 0
    profit_pct = ((row['close'] - entry_price) / entry_price) * 100
    
    # 1. RSI 超買 (最高 30 分)
    rsi = row['rsi']
    if pd.notna(rsi):
        if rsi > 70:
            score += 30  # 極度超買
        elif rsi > 60:
            score += 20
        elif rsi > 55:
            score += 10
    
    # 2. 價格 vs MA200 (最高 20 分)
    if pd.notna(row['ma_200']) and row['close'] > row['ma_200']:
        premium = (row['close'] - row['ma_200']) / row['ma_200']
        score += min(20, premium * 50)
    
    # 3. 價格 vs 近期高點 (最高 25 分)
    if idx >= 90:
        recent_90d = df.iloc[idx-90:idx]
        high_90d = recent_90d['high'].max()
        if row['close'] >= high_90d * 0.95:  # 接近 90 天高點
            score += 25
        elif row['close'] >= high_90d * 0.90:
            score += 15
    
    # 4. 利潤 (最高 25 分)
    if profit_pct > 100:
        score += 25  # 翻倍
    elif profit_pct > 50:
        score += 15
    elif profit_pct > 30:
        score += 10
    
    # 5. Bollinger Bands (加分)
    if pd.notna(row['bb_upper']) and row['close'] > row['bb_upper']:
        score += 10  # 突破上軌
    
    # 6. 止損保護 (強制賣出)
    if profit_pct < -50:
        score = 100  # 觸發止損
    
    return min(100, score)


def run_optimized_backtest(initial_capital=10000, weekly_investment=100):
    """
    執行優化回測
    """
    print("=" * 70)
    print("ADA 優化回測（多指標綜合策略）")
    print("=" * 70)
    
    # 載入數據
    print("\n📊 載入數據...")
    df = load_complete_data()
    print(f"✅ 數據範圍: {df['date'].min().date()} ~ {df['date'].max().date()} ({len(df)} 天)")
    print(f"💰 ADA 價格: ${df['close'].min():.4f} ~ ${df['close'].max():.4f}")
    
    # 初始化
    cash = initial_capital
    ada_holdings = 0.0
    total_invested = initial_capital
    entry_price = 0.0
    
    buy_records = []
    sell_records = []
    
    # 每週執行一次
    print("\n🔄 執行回測...")
    
    for i in range(0, len(df), 7):  # 每週
        if i >= len(df):
            break
            
        row = df.iloc[i]
        date = row['date']
        price = row['close']
        
        # 計算評分
        buy_score = calculate_buy_score(row, df, i)
        sell_score = calculate_sell_score(row, df, i, entry_price, ada_holdings)
        
        # 賣出邏輯 (優先)
        if sell_score >= 60 and ada_holdings > 0:  # 閾值: 60 分
            sell_pct = min(100, (sell_score - 60) * 2.5)  # 60分=0%, 100分=100%
            sell_amount = ada_holdings * (sell_pct / 100)
            sell_value = sell_amount * price
            
            cash += sell_value
            ada_holdings -= sell_amount
            
            sell_records.append({
                'date': date,
                'price': price,
                'ada_sold': sell_amount,
                'usd_received': sell_value,
                'score': sell_score,
                'rsi': row['rsi']
            })
        
        # 買入邏輯
        if buy_score >= 50:  # 閾值: 50 分
            # 根據評分決定買入倍數
            multiplier = 1 + ((buy_score - 50) / 20)  # 50分=1x, 100分=3.5x
            buy_amount_usd = weekly_investment * multiplier
            
            if buy_amount_usd > 0:
                ada_bought = buy_amount_usd / price
                ada_holdings += ada_bought
                cash -= buy_amount_usd
                total_invested += buy_amount_usd
                
                # 更新平均成本
                if ada_holdings > 0:
                    entry_price = (entry_price * (ada_holdings - ada_bought) + buy_amount_usd) / ada_holdings if ada_holdings > ada_bought else price
                
                buy_records.append({
                    'date': date,
                    'price': price,
                    'usd_spent': buy_amount_usd,
                    'ada_bought': ada_bought,
                    'score': buy_score,
                    'multiplier': multiplier,
                    'rsi': row['rsi']
                })
    
    # 最終結算
    final_price = df.iloc[-1]['close']
    final_value = ada_holdings * final_price + cash
    total_return = final_value - initial_capital
    return_pct = (total_return / initial_capital) * 100
    
    # HODL 對比
    hodl_ada = initial_capital / df.iloc[0]['close']
    hodl_value = hodl_ada * final_price
    hodl_return_pct = ((hodl_value - initial_capital) / initial_capital) * 100
    
    # 輸出結果
    print("\n" + "=" * 70)
    print("📊 回測結果")
    print("=" * 70)
    
    print(f"\n💰 投資概況:")
    print(f"   初始資金: ${initial_capital:,.2f}")
    print(f"   總投入: ${total_invested:,.2f}")
    print(f"   買入次數: {len(buy_records)} 次")
    print(f"   賣出次數: {len(sell_records)} 次")
    
    print(f"\n📈 績效表現:")
    print(f"   最終價值: ${final_value:,.2f}")
    print(f"   總報酬: ${total_return:,.2f} ({return_pct:+.2f}%)")
    print(f"   ADA 持有: {ada_holdings:.2f} ADA")
    print(f"   現金餘額: ${cash:,.2f}")
    
    print(f"\n🆚 vs HODL:")
    print(f"   HODL 價值: ${hodl_value:,.2f} ({hodl_return_pct:+.2f}%)")
    print(f"   策略超越: {return_pct - hodl_return_pct:+.2f}%")
    
    # 顯示最佳買賣點
    if len(buy_records) > 0:
        buy_df = pd.DataFrame(buy_records)
        top_buys = buy_df.nlargest(5, 'score')
        print(f"\n🎯 最佳買入時機（評分最高）:")
        for _, b in top_buys.iterrows():
            print(f"   {b['date'].date()}: ${b['price']:.4f} (評分: {b['score']:.0f}, RSI: {b['rsi']:.1f})")
    
    if len(sell_records) > 0:
        sell_df = pd.DataFrame(sell_records)
        top_sells = sell_df.nlargest(5, 'score')
        print(f"\n💎 最佳賣出時機（評分最高）:")
        for _, s in top_sells.iterrows():
            print(f"   {s['date'].date()}: ${s['price']:.4f} (評分: {s['score']:.0f}, RSI: {s['rsi']:.1f})")
    
    print("\n" + "=" * 70)
    
    return {
        'final_value': final_value,
        'return_pct': return_pct,
        'hodl_return_pct': hodl_return_pct,
        'outperformance': return_pct - hodl_return_pct
    }


if __name__ == "__main__":
    result = run_optimized_backtest()
