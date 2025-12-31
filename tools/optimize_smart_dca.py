#!/usr/bin/env python3
# tools/optimize_smart_dca.py
"""
Smart DCA 參數優化
系統性測試各種參數組合找出最佳配置
"""

import pandas as pd
import pandas_ta as ta
from itertools import product

def test_smart_dca_params(df_weekly, params):
    """測試指定參數的Smart DCA策略"""
    rsi_buy_low = params['rsi_buy_low']
    rsi_buy_mid = params['rsi_buy_mid']
    rsi_sell_high = params['rsi_sell_high']
    buy_multiplier_low = params['buy_multiplier_low']
    buy_multiplier_mid = params['buy_multiplier_mid']
    sell_multiplier_high = params['sell_multiplier_high']
    sell_ratio = params['sell_ratio']
    ma_multiplier = params['ma_multiplier']
    reserve_use_ratio = params['reserve_use_ratio']
    
    weekly_cash = 250
    total_cash = 0
    btc = 0
    usdt_reserve = 0
    sell_count = 0
    
    for idx, row in df_weekly.iterrows():
        if pd.isna(row['rsi']):
            continue
        
        price = row['close']
        rsi = row['rsi']
        
        total_cash += weekly_cash
        
        # 賣出邏輯
        if btc > 0 and not pd.isna(row['ma200']):
            ma200 = row['ma200']
            if rsi > rsi_sell_high and price > ma200 * ma_multiplier:
                sell_btc = btc * sell_ratio
                usdt_reserve += sell_btc * price
                btc -= sell_btc
                sell_count += 1
        
        # 買入邏輯
        buy_amount = weekly_cash
        
        if rsi < rsi_buy_low:
            buy_amount *= buy_multiplier_low
        elif rsi < rsi_buy_mid:
            buy_amount *= buy_multiplier_mid
        elif rsi > rsi_sell_high:
            buy_amount *= sell_multiplier_high
        
        # 動用儲備
        if usdt_reserve > 0 and rsi < rsi_buy_mid:
            extra = min(usdt_reserve * reserve_use_ratio, weekly_cash)
            buy_amount += extra
            usdt_reserve -= extra
        
        btc += buy_amount / price
    
    final_price = df_weekly.iloc[-1]['close']
    total_value = btc * final_price + usdt_reserve
    roi = ((total_value / total_cash) - 1) * 100
    
    return {
        'roi': roi,
        'total_value': total_value,
        'btc': btc,
        'usdt': usdt_reserve,
        'sell_count': sell_count,
        'params': params
    }


def optimize_parameters():
    """參數網格搜索"""
    # 載入數據
    df = pd.read_csv('data/backtest/BTC_2021_2024_daily.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    df_weekly = df.resample('W').last().dropna()
    df_weekly['rsi'] = ta.rsi(df_weekly['close'], length=14)
    df_weekly['ma200'] = ta.sma(df_weekly['close'], length=200)
    
    print("="*70)
    print("Smart DCA 參數優化")
    print("="*70)
    
    # 定義參數網格
    param_grid = {
        'rsi_buy_low': [20, 25, 30],
        'rsi_buy_mid': [30, 35, 40],
        'rsi_sell_high': [70, 75, 80],
        'buy_multiplier_low': [1.8, 2.0, 2.5],
        'buy_multiplier_mid': [1.3, 1.5, 1.7],
        'sell_multiplier_high': [0.5, 0.7, 0.8],
        'sell_ratio': [0.2, 0.3, 0.4],
        'ma_multiplier': [1.2, 1.3, 1.4],
        'reserve_use_ratio': [0.3, 0.5, 0.7]
    }
    
    # 快速測試：只測試關鍵參數組合
    print("\n階段1：快速測試關鍵參數...")
    
    key_tests = [
        # 基準（當前）
        {'rsi_buy_low': 25, 'rsi_buy_mid': 35, 'rsi_sell_high': 75,
         'buy_multiplier_low': 2.0, 'buy_multiplier_mid': 1.5, 'sell_multiplier_high': 0.7,
         'sell_ratio': 0.3, 'ma_multiplier': 1.3, 'reserve_use_ratio': 0.5},
        
        # 激進買入
        {'rsi_buy_low': 20, 'rsi_buy_mid': 30, 'rsi_sell_high': 75,
         'buy_multiplier_low': 2.5, 'buy_multiplier_mid': 1.7, 'sell_multiplier_high': 0.7,
         'sell_ratio': 0.3, 'ma_multiplier': 1.3, 'reserve_use_ratio': 0.7},
        
        # 保守賣出
        {'rsi_buy_low': 25, 'rsi_buy_mid': 35, 'rsi_sell_high': 70,
         'buy_multiplier_low': 2.0, 'buy_multiplier_mid': 1.5, 'sell_multiplier_high': 0.7,
         'sell_ratio': 0.2, 'ma_multiplier': 1.2, 'reserve_use_ratio': 0.5},
        
        # 激進賣出
        {'rsi_buy_low': 25, 'rsi_buy_mid': 35, 'rsi_sell_high': 80,
         'buy_multiplier_low': 2.0, 'buy_multiplier_mid': 1.5, 'sell_multiplier_high': 0.7,
         'sell_ratio': 0.4, 'ma_multiplier': 1.4, 'reserve_use_ratio': 0.5},
        
        # 平衡型
        {'rsi_buy_low': 25, 'rsi_buy_mid': 40, 'rsi_sell_high': 75,
         'buy_multiplier_low': 2.0, 'buy_multiplier_mid': 1.3, 'sell_multiplier_high': 0.5,
         'sell_ratio': 0.3, 'ma_multiplier': 1.3, 'reserve_use_ratio': 0.3},
    ]
    
    results = []
    for i, params in enumerate(key_tests):
        result = test_smart_dca_params(df_weekly, params)
        results.append(result)
        print(f"  測試 {i+1}: ROI = {result['roi']:.2f}%")
    
    # 找出最佳
    best = max(results, key=lambda x: x['roi'])
    
    print(f"\n{'='*70}")
    print("最佳結果")
    print(f"{'='*70}")
    print(f"報酬率: {best['roi']:.2f}%")
    print(f"總資產: ${best['total_value']:,.2f}")
    print(f"BTC: {best['btc']:.6f}")
    print(f"USDT: ${best['usdt']:,.2f}")
    print(f"賣出次數: {best['sell_count']}")
    
    print(f"\n最佳參數:")
    for key, value in best['params'].items():
        print(f"  {key}: {value}")
    
    # 與基準比較
    baseline_roi = 154.47  # 當前版本
    improvement = best['roi'] - baseline_roi
    
    print(f"\n{'='*70}")
    print(f"vs 當前版本 (+154.47%): {improvement:+.2f}%")
    if improvement > 0:
        print(f"✅ 找到更優配置！")
    else:
        print(f"⚪ 當前配置已經很好")

if __name__ == "__main__":
    optimize_parameters()
