#!/usr/bin/env python3
# tools/check_recent_signals.py
"""
檢查近期行情是否觸發交易信號
"""

import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.smc_detector import SMCDetector


def check_silver_bullet_signals(df):
    """檢查 Silver Bullet 信號"""
    df['ema_200'] = ta.ema(df['close'], length=200)
    
    signals = []
    near_signals = []
    
    for i in range(210, len(df)):
        current = df.iloc[i]
        prev_hour = df.iloc[i-4:i]
        
        # 時段檢查（UTC）
        hour = current['timestamp'].hour
        in_session = (2 <= hour < 5) or (10 <= hour < 11)
        
        # 掃蕩形態
        lh_low = prev_hour['low'].min()
        lh_high = prev_hour['high'].max()
        
        # LONG 信號
        if current['low'] < lh_low and current['close'] > lh_low:
            if current['close'] > current['ema_200']:
                if in_session:
                    signals.append({
                        'time': current['timestamp'],
                        'type': 'LONG',
                        'price': current['close'],
                        'reason': '掃蕩低點 + EMA200上方 + 時段正確',
                        'ema': current['ema_200']
                    })
                else:
                    near_signals.append({
                        'time': current['timestamp'],
                        'type': 'LONG',
                        'price': current['close'],
                        'reason': '掃蕩低點 + EMA200上方，但時段不對',
                        'missing': '非交易時段'
                    })
            else:
                near_signals.append({
                    'time': current['timestamp'],
                    'type': 'LONG',
                    'price': current['close'],
                    'reason': '掃蕩低點，但收盤在 EMA200 下方',
                    'missing': f'EMA200: {current["ema_200"]:.2f}, Close: {current["close"]:.2f}'
                })
        
        # SHORT 信號
        if current['high'] > lh_high and current['close'] < lh_high:
            if current['close'] < current['ema_200']:
                if in_session:
                    signals.append({
                        'time': current['timestamp'],
                        'type': 'SHORT',
                        'price': current['close'],
                        'reason': '掃蕩高點 + EMA200下方 + 時段正確',
                        'ema': current['ema_200']
                    })
                else:
                    near_signals.append({
                        'time': current['timestamp'],
                        'type': 'SHORT',
                        'price': current['close'],
                        'reason': '掃蕩高點 + EMA200下方，但時段不對',
                        'missing': '非交易時段'
                    })
            else:
                near_signals.append({
                    'time': current['timestamp'],
                    'type': 'SHORT',
                    'price': current['close'],
                    'reason': '掃蕩高點，但收盤在 EMA200 上方',
                    'missing': f'EMA200: {current["ema_200"]:.2f}, Close: {current["close"]:.2f}'
                })
    
    return signals, near_signals


def main():
    print("=" * 70)
    print("🔍 檢查 12/27-12/29 行情信號")
    print("=" * 70)
    
    # 載入數據
    try:
        df = pd.read_csv('temp_btc_recent.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except:
        print("❌ 找不到數據文件，請先載入數據")
        return
    
    print(f"\n📊 數據範圍: {df.iloc[0]['timestamp']} 到 {df.iloc[-1]['timestamp']}")
    print(f"   總K線數: {len(df)}")
    
    # 篩選 12/27-12/29
    target_start = pd.to_datetime('2024-12-27')
    target_end = pd.to_datetime('2024-12-29 23:59:59')
    
    df_target = df[(df['timestamp'] >= target_start) & (df['timestamp'] <= target_end)]
    print(f"   目標期間K線: {len(df_target)}")
    
    # 檢查 Silver Bullet
    print("\n" + "=" * 70)
    print("🎯 Silver Bullet 信號檢查")
    print("=" * 70)
    
    signals, near_signals = check_silver_bullet_signals(df)
    
    # 過濾目標期間
    target_signals = [s for s in signals if target_start <= s['time'] <= target_end]
    target_near = [s for s in near_signals if target_start <= s['time'] <= target_end]
    
    if target_signals:
        print(f"\n✅ 發現 {len(target_signals)} 個有效信號：")
        for s in target_signals:
            print(f"\n   時間: {s['time']}")
            print(f"   類型: {s['type']}")
            print(f"   價格: ${s['price']:.2f}")
            print(f"   原因: {s['reason']}")
    else:
        print("\n❌ 沒有發現有效信號")
    
    if target_near:
        print(f"\n⚠️  發現 {len(target_near)} 個接近但未達標的信號：")
        for s in target_near[:5]:  # 只顯示前5個
            print(f"\n   時間: {s['time']}")
            print(f"   類型: {s['type']}")
            print(f"   價格: ${s['price']:.2f}")
            print(f"   原因: {s['reason']}")
            print(f"   缺少: {s['missing']}")
    
    # 價格統計
    print("\n" + "=" * 70)
    print("📈 價格變化統計")
    print("=" * 70)
    
    if len(df_target) > 0:
        print(f"\n   最高價: ${df_target['high'].max():.2f}")
        print(f"   最低價: ${df_target['low'].min():.2f}")
        print(f"   波動幅度: ${df_target['high'].max() - df_target['low'].min():.2f}")
        print(f"   波動率: {(df_target['high'].max() - df_target['low'].min()) / df_target['low'].min() * 100:.2f}%")


if __name__ == "__main__":
    main()
