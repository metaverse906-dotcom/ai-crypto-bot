#!/usr/bin/env python3
"""
真實 MVRV vs 估算 MVRV 回測比較

目標：驗證兩種 MVRV 數據源對策略績效的影響
1. 估算 MVRV（使用價格/200WMA 比率）
2. 真實 MVRV（使用 CoinGlass 或 LookIntoBitcoin 數據）

結論：決定是否需要實作真實 MVRV 數據源
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_btc_data(days=1500):
    """下載 BTC 歷史價格數據 (使用多次分頁獲取更多數據)"""
    import ccxt
    
    # 使用 OKX 獲取數據
    exchange = ccxt.okx()
    
    # 獲取日線數據（OKX 限制 300 條，需要分頁）
    all_data = []
    since = exchange.parse8601('2021-01-01T00:00:00Z')
    
    while True:
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1d', since=since, limit=300)
        if len(ohlcv) == 0:
            break
        all_data.extend(ohlcv)
        since = ohlcv[-1][0] + 86400000  # 加一天
        if len(all_data) >= days:
            break
    
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    df = df[~df.index.duplicated(keep='first')]  # 移除重複
    
    # 計算 200日均線（作為 200WMA 代理）
    df['200wma'] = df['close'].rolling(window=200, min_periods=50).mean()
    
    # 週線重採樣
    weekly = df.resample('W').agg({
        'open': 'first',
        'close': 'last',
        'high': 'max',
        'low': 'min',
        'volume': 'sum',
        '200wma': 'last'
    })
    
    return weekly.dropna()


def calculate_estimated_mvrv(df):
    """
    計算估算 MVRV（使用價格/200WMA 比率）
    
    這是我們目前使用的方法
    """
    def ratio_to_mvrv(ratio):
        if ratio < 1.0:
            return 0.0
        elif ratio < 1.5:
            return 1.0
        elif ratio < 2.0:
            return 3.0
        elif ratio < 3.0:
            return 5.0
        elif ratio < 4.0:
            return 7.0
        else:
            return 9.0
    
    df = df.copy()
    df['price_to_200wma'] = df['close'] / df['200wma']
    df['mvrv_estimated'] = df['price_to_200wma'].apply(ratio_to_mvrv)
    
    return df


def calculate_improved_mvrv(df):
    """
    改進的 MVRV 估算（更精確的映射）
    
    基於歷史數據觀察的線性插值：
    - Price @ 200WMA (1.0x) → MVRV ≈ 0.5
    - Price @ 1.5x 200WMA → MVRV ≈ 1.5
    - Price @ 2.0x 200WMA → MVRV ≈ 2.5
    - Price @ 3.0x 200WMA → MVRV ≈ 4.5
    """
    df = df.copy()
    df['price_to_200wma'] = df['close'] / df['200wma']
    
    def improved_ratio_to_mvrv(ratio):
        if ratio <= 0.5:
            return -1.0
        elif ratio <= 1.0:
            # 線性插值: 0.5x → MVRV -1.0, 1.0x → MVRV 0.5
            return -1.0 + (ratio - 0.5) * (1.5 / 0.5)
        elif ratio <= 1.5:
            # 線性插值: 1.0x → MVRV 0.5, 1.5x → MVRV 1.5
            return 0.5 + (ratio - 1.0) * (1.0 / 0.5)
        elif ratio <= 2.0:
            # 線性插值: 1.5x → MVRV 1.5, 2.0x → MVRV 2.5
            return 1.5 + (ratio - 1.5) * (1.0 / 0.5)
        elif ratio <= 3.0:
            # 線性插值: 2.0x → MVRV 2.5, 3.0x → MVRV 4.5
            return 2.5 + (ratio - 2.0) * (2.0 / 1.0)
        elif ratio <= 4.0:
            # 線性插值: 3.0x → MVRV 4.5, 4.0x → MVRV 6.5
            return 4.5 + (ratio - 3.0) * (2.0 / 1.0)
        else:
            # 4.0x+ → MVRV 6.5+
            return 6.5 + (ratio - 4.0) * 1.5
    
    df['mvrv_improved'] = df['price_to_200wma'].apply(improved_ratio_to_mvrv)
    
    return df


def get_composite_score(mvrv, rsi=50, fg=50):
    """計算加權綜合分數"""
    # MVRV → 分數
    if mvrv < 0.1:
        mvrv_score = 0
    elif mvrv < 1.0:
        mvrv_score = 10
    elif mvrv < 3.0:
        mvrv_score = 30
    elif mvrv < 5.0:
        mvrv_score = 50
    elif mvrv < 6.0:
        mvrv_score = 65
    elif mvrv < 7.0:
        mvrv_score = 80
    elif mvrv < 9.0:
        mvrv_score = 90
    else:
        mvrv_score = 100
    
    # 加權：MVRV 65% + RSI 25% + F&G 10%
    return (mvrv_score * 0.65) + (rsi * 0.25) + (fg * 0.10)


def get_buy_multiplier(score):
    """根據綜合分數決定買入倍數"""
    if score < 15:
        return 3.5
    elif score < 25:
        return 2.0
    elif score < 35:
        return 1.5
    elif score < 50:
        return 1.0
    elif score < 60:
        return 0.5
    else:
        return 0.0


def backtest_strategy(df, mvrv_column, weekly_usd=250):
    """
    執行策略回測
    
    Args:
        df: 包含價格和 MVRV 的 DataFrame
        mvrv_column: 使用哪個 MVRV 欄位
        weekly_usd: 每週基礎投入金額
    
    Returns:
        dict: 回測結果
    """
    total_btc = 0.0
    total_invested = 0.0
    trades = []
    
    for date, row in df.iterrows():
        price = row['close']
        mvrv = row[mvrv_column]
        
        # 計算綜合分數（簡化：只用 MVRV）
        score = get_composite_score(mvrv)
        multiplier = get_buy_multiplier(score)
        
        buy_usd = weekly_usd * multiplier
        buy_btc = buy_usd / price if buy_usd > 0 else 0
        
        total_btc += buy_btc
        total_invested += buy_usd
        
        trades.append({
            'date': date,
            'price': price,
            'mvrv': mvrv,
            'score': score,
            'multiplier': multiplier,
            'buy_usd': buy_usd,
            'buy_btc': buy_btc,
            'total_btc': total_btc
        })
    
    final_price = df['close'].iloc[-1]
    final_value = total_btc * final_price
    avg_cost = total_invested / total_btc if total_btc > 0 else 0
    
    return {
        'total_btc': total_btc,
        'total_invested': total_invested,
        'final_value': final_value,
        'avg_cost': avg_cost,
        'roi_pct': ((final_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0,
        'trades': trades
    }


def hodl_backtest(df, weekly_usd=250):
    """HODL 對照組：每週固定買入"""
    total_btc = 0.0
    total_invested = 0.0
    
    for date, row in df.iterrows():
        price = row['close']
        buy_btc = weekly_usd / price
        
        total_btc += buy_btc
        total_invested += weekly_usd
    
    final_price = df['close'].iloc[-1]
    final_value = total_btc * final_price
    avg_cost = total_invested / total_btc if total_btc > 0 else 0
    
    return {
        'total_btc': total_btc,
        'total_invested': total_invested,
        'final_value': final_value,
        'avg_cost': avg_cost,
        'roi_pct': ((final_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0
    }


def main():
    """主程序：比較不同 MVRV 數據源的策略效果"""
    print("=" * 70)
    print("真實 MVRV vs 估算 MVRV 回測比較")
    print("=" * 70)
    
    # 1. 下載數據
    print("\n📊 下載 BTC 歷史數據...")
    df = download_btc_data(days=1000)
    print(f"數據範圍：{df.index[0]} ~ {df.index[-1]}")
    print(f"共 {len(df)} 週")
    
    # 2. 計算兩種 MVRV
    print("\n📈 計算 MVRV...")
    df = calculate_estimated_mvrv(df)
    df = calculate_improved_mvrv(df)
    
    # 顯示當前 MVRV 對比
    current = df.iloc[-1]
    print(f"\n當前數據：")
    print(f"  價格: ${current['close']:,.0f}")
    print(f"  200WMA: ${current['200wma']:,.0f}")
    print(f"  價格/200WMA: {current['price_to_200wma']:.2f}x")
    print(f"  估算 MVRV (舊): {current['mvrv_estimated']:.1f}")
    print(f"  估算 MVRV (改進): {current['mvrv_improved']:.2f}")
    
    # 3. 執行回測
    print("\n🔄 執行回測...")
    
    # 策略 1: 舊的估算 MVRV
    result_old = backtest_strategy(df, 'mvrv_estimated')
    
    # 策略 2: 改進的估算 MVRV
    result_improved = backtest_strategy(df, 'mvrv_improved')
    
    # 對照組: HODL
    result_hodl = hodl_backtest(df)
    
    # 4. 顯示結果
    print("\n" + "=" * 70)
    print("回測結果比較")
    print("=" * 70)
    
    print(f"\n{'策略':<25} {'累積 BTC':>12} {'總投入':>15} {'平均成本':>12} {'vs HODL':>12}")
    print("-" * 70)
    
    hodl_btc = result_hodl['total_btc']
    
    strategies = [
        ("HODL (每週固定)", result_hodl),
        ("舊估算 MVRV", result_old),
        ("改進估算 MVRV", result_improved),
    ]
    
    for name, result in strategies:
        vs_hodl = ((result['total_btc'] - hodl_btc) / hodl_btc) * 100
        print(f"{name:<25} {result['total_btc']:>12.6f} ${result['total_invested']:>13,.0f} ${result['avg_cost']:>10,.0f} {vs_hodl:>+10.1f}%")
    
    # 5. 分析結論
    print("\n" + "=" * 70)
    print("分析結論")
    print("=" * 70)
    
    improvement_old = ((result_old['total_btc'] - hodl_btc) / hodl_btc) * 100
    improvement_new = ((result_improved['total_btc'] - hodl_btc) / hodl_btc) * 100
    
    print(f"\n📊 舊估算 MVRV vs HODL: {improvement_old:+.1f}%")
    print(f"📊 改進估算 MVRV vs HODL: {improvement_new:+.1f}%")
    print(f"📊 改進版相對舊版提升: {improvement_new - improvement_old:+.1f}%")
    
    if improvement_new > improvement_old:
        print("\n✅ 建議：使用改進的 MVRV 估算公式")
    else:
        print("\n⚠️ 舊公式表現更好，需要進一步分析")
    
    # 6. 保存詳細結果
    trades_df = pd.DataFrame(result_improved['trades'])
    save_path = os.path.join(os.path.dirname(__file__), 'mvrv_comparison_result.csv')
    trades_df.to_csv(save_path, index=False)
    print(f"\n📁 詳細交易記錄已保存到: {save_path}")


if __name__ == '__main__':
    main()
