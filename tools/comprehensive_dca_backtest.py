#!/usr/bin/env python3
# tools/comprehensive_dca_backtest.py
"""
完整 DCA 回測：2021-2024 + Bootstrap 統計驗證
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
import ccxt
import time

# ========== 數據下載 ==========

def download_full_data():
    """下載 2021-2024 完整數據"""
    print("下載 2021-2024 BTC 數據...")
    
    exchange = ccxt.binance()
    start = datetime(2021, 1, 1)
    end = datetime(2024, 12, 31)
    
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    
    all_data = []
    current_ms = start_ms
    
    while current_ms < end_ms:
        try:
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=current_ms, limit=1000)
            if not ohlcv:
                break
            all_data.extend(ohlcv)
            current_ms = ohlcv[-1][0] + 86400000
            print(f"已下載 {len(all_data)} 天...", end='\r')
            time.sleep(0.5)
        except Exception as e:
            print(f"\n錯誤: {e}")
            time.sleep(2)
    
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset=['timestamp'])
    df.to_csv('data/backtest/BTC_2021_2024_daily.csv', index=False)
    
    print(f"\n✅ 完成！{len(df)} 天數據")
    return df


# ========== DCA 策略 ==========

def normal_dca(df, weekly_amount=250):
    """普通 DCA：每週固定金額"""
    df = df.copy()
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    
    df_weekly = df.resample('W').last().dropna()
    
    total_invested = 0
    total_btc = 0
    
    for idx, row in df_weekly.iterrows():
        price = row['close']
        btc = weekly_amount / price
        total_btc += btc
        total_invested += weekly_amount
    
    final_value = total_btc * df_weekly.iloc[-1]['close']
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'invested': total_invested,
        'btc': total_btc,
        'final_value': final_value,
        'roi': roi,
        'avg_cost': total_invested / total_btc if total_btc > 0 else 0
    }


def smart_dca_conservative(df, base_amount=250):
    """保守 Smart DCA：只在極端時調整"""
    df = df.copy()
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    
    df_weekly = df.resample('W').last().dropna()
    
    # 計算 RSI
    df_weekly['rsi'] = ta.rsi(df_weekly['close'], length=14)
    
    total_invested = 0
    total_btc = 0
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        
        # 保守調整：只在極端時
        if rsi < 25:  # 極度超賣
            amount = base_amount * 2
        elif rsi < 35:
            amount = base_amount * 1.3
        elif rsi > 80:  # 極度超買
            amount = base_amount * 0.7
        elif rsi > 75:
            amount = base_amount * 0.85
        else:
            amount = base_amount
        
        btc = amount / price
        total_btc += btc
        total_invested += amount
    
    final_value = total_btc * df_weekly.iloc[-1]['close']
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'invested': total_invested,
        'btc': total_btc,
        'final_value': final_value,
        'roi': roi,
        'avg_cost': total_invested / total_btc if total_btc > 0 else 0
    }


def smart_dca_aggressive(df, base_amount=250):
    """激進 Smart DCA：顯著調整"""
    df = df.copy()
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    
    df_weekly = df.resample('W').last().dropna()
    df_weekly['rsi'] = ta.rsi(df_weekly['close'], length=14)
    
    total_invested = 0
    total_btc = 0
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        
        # 激進調整
        if rsi < 30:
            amount = base_amount * 2.5
        elif rsi < 40:
            amount = base_amount * 1.8
        elif rsi > 70:
            amount = base_amount * 0.4
        elif rsi > 60:
            amount = base_amount * 0.7
        else:
            amount = base_amount
        
        btc = amount / price
        total_btc += btc
        total_invested += amount
    
    final_value = total_btc * df_weekly.iloc[-1]['close']
    roi = ((final_value / total_invested) - 1) * 100
    
    return {
        'invested': total_invested,
        'btc': total_btc,
        'final_value': final_value,
        'roi': roi,
        'avg_cost': total_invested / total_btc if total_btc > 0 else 0
    }


# ========== Bootstrap 統計驗證 ==========

def bootstrap_test(df, strategy_func, n_iterations=100):
    """Bootstrap 重抽樣測試策略穩定性"""
    print(f"\n執行 Bootstrap 測試（{n_iterations} 次）...")
    
    df = df.copy()
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    
    df_weekly = df.resample('W').last().dropna()
    n_weeks = len(df_weekly)
    
    results = []
    
    for i in range(n_iterations):
        # 隨機抽樣（有放回）
        sample_indices = np.random.choice(n_weeks, size=n_weeks, replace=True)
        df_sample = df_weekly.iloc[sample_indices].copy()
        df_sample = df_sample.sort_index()
        
        # 執行策略 - 直接傳遞已處理的df
        result = strategy_func(df_sample)
        results.append(result['roi'])
        
        if (i + 1) % 20 == 0:
            print(f"  進度: {i+1}/{n_iterations}", end='\r')
    
    return {
        'mean_roi': np.mean(results),
        'std_roi': np.std(results),
        'median_roi': np.median(results),
        'ci_95': (np.percentile(results, 2.5), np.percentile(results, 97.5))
    }


# ========== 主程序 ==========

def main():
    print("="*70)
    print("完整 DCA 回測：2021-2024 + Bootstrap 驗證")
    print("="*70)
    
    # 下載或載入數據
    try:
        df = pd.read_csv('data/backtest/BTC_2021_2024_daily.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"✅ 載入現有數據：{len(df)} 天")
    except:
        df = download_full_data()
    
    print(f"\n期間：{df.iloc[0]['timestamp'].date()} 到 {df.iloc[-1]['timestamp'].date()}")
    print(f"價格範圍：${df['low'].min():.0f} - ${df['high'].max():.0f}")
    
    # 設置時間索引
    df.set_index('timestamp', inplace=True)
    
    # 基礎回測
    print("\n" + "="*70)
    print("策略回測")
    print("="*70)
    
    normal = normal_dca(df.copy())
    smart_cons = smart_dca_conservative(df.copy())
    smart_agg = smart_dca_aggressive(df.copy())
    
    strategies = [
        ('普通 DCA', normal),
        ('Smart DCA (保守)', smart_cons),
        ('Smart DCA (激進)', smart_agg)
    ]
    
    for name, result in strategies:
        print(f"\n【{name}】")
        print(f"  投入：${result['invested']:,.0f}")
        print(f"  BTC：{result['btc']:.6f}")
        print(f"  平均成本：${result['avg_cost']:,.2f}")
        print(f"  最終價值：${result['final_value']:,.2f}")
        print(f"  報酬率：{result['roi']:.2f}%")
    
    # Bootstrap 測試（選擇性）
    print("\n" + "="*70)
    print("Bootstrap 統計驗證")
    print("="*70)
    print("執行100次重抽樣測試...")
    
    boot_normal = bootstrap_test(df.copy(), normal_dca, 100)
    boot_smart = bootstrap_test(df.copy(), smart_dca_conservative, 100)
    
    print("\n\n【Bootstrap 結果】")
    print(f"普通 DCA：{boot_normal['mean_roi']:.2f}% ± {boot_normal['std_roi']:.2f}%")
    print(f"  95% CI: [{boot_normal['ci_95'][0]:.2f}%, {boot_normal['ci_95'][1]:.2f}%]")
    print(f"\nSmart DCA：{boot_smart['mean_roi']:.2f}% ± {boot_smart['std_roi']:.2f}%")
    print(f"  95% CI: [{boot_smart['ci_95'][0]:.2f}%, {boot_smart['ci_95'][1]:.2f}%]")
    
    print("\n" + "="*70)
    print("完成！")
    print("="*70)


if __name__ == "__main__":
    main()
