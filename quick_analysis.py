#!/usr/bin/env python3
"""快速分析 12/27-12/29 行情"""
import pandas as pd
import pandas_ta as ta

# 載入數據
df = pd.read_csv('temp_btc_recent.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 篩選目標期間
target = df[(df['timestamp'] >= '2024-12-27') & (df['timestamp'] <= '2024-12-29 23:59:59')]

print("=" * 70)
print("📊 BTC/USDT 12/27-12/29 行情分析")
print("=" * 70)

print(f"\n數據概況：")
print(f"  K線數量: {len(target)}")
print(f"  時間範圍: {target.iloc[0]['timestamp']} 到 {target.iloc[-1]['timestamp']}")

print(f"\n價格統計：")
print(f"  最高價: ${target['high'].max():.2f}")
print(f"  最低價: ${target['low'].min():.2f}")
print(f"  波動幅度: ${target['high'].max() - target['low'].min():.2f}")
print(f"  波動率: {(target['high'].max() - target['low'].min()) / target['low'].min() * 100:.2f}%")

# 計算 EMA 200
df['ema_200'] = ta.ema(df['close'], length=200)

# 檢查 Silver Bullet 條件
print("\n" + "=" * 70)
print("🎯 Silver Bullet 策略分析")
print("=" * 70)

signals_found = 0
near_misses = 0

for i in range(210, len(df)):
    row = df.iloc[i]
    
    # 只看目標期間
    if not ('2024-12-27' <= str(row['timestamp']) <= '2024-12-29 23:59'):
        continue
    
    prev_4h = df.iloc[i-4:i]
    lh_low = prev_4h['low'].min()
    lh_high = prev_4h['high'].max()
    
    hour = row['timestamp'].hour
    in_session = (2 <= hour < 5) or (10 <= hour < 11)
    
    # 檢查 LONG
    if row['low'] < lh_low and row['close'] > lh_low:
        if row['close'] > row['ema_200'] and in_session:
            signals_found += 1
            print(f"\n✅ LONG 信號 #{signals_found}")
            print(f"   時間: {row['timestamp']}")
            print(f"   價格: ${row['close']:.2f}")
            print(f"   EMA200: ${row['ema_200']:.2f}")
        elif row['close'] > row['ema_200']:
            near_misses += 1
            print(f"\n⚠️  接近 LONG 信號 (時段不對)")
            print(f"   時間: {row['timestamp']} (UTC {hour}:xx)")
            print(f"   價格: ${row['close']:.2f}")
            print(f"   需要: 02:00-05:00 或 10:00-11:00 UTC")
        else:
            near_misses += 1
            print(f"\n⚠️  接近 LONG 信號 (EMA未突破)")
            print(f"   時間: {row['timestamp']}")
            print(f"   價格: ${row['close']:.2f}, EMA200: ${row['ema_200']:.2f}")
            print(f"   差距: ${row['ema_200'] - row['close']:.2f}")
    
    # 檢查 SHORT  
    if row['high'] > lh_high and row['close'] < lh_high:
        if row['close'] < row['ema_200'] and in_session:
            signals_found += 1
            print(f"\n✅ SHORT 信號 #{signals_found}")
            print(f"   時間: {row['timestamp']}")
            print(f"   價格: ${row['close']:.2f}")
            print(f"   EMA200: ${row['ema_200']:.2f}")
        elif row['close'] < row['ema_200']:
            near_misses += 1
            print(f"\n⚠️  接近 SHORT 信號 (時段不對)")
            print(f"   時間: {row['timestamp']} (UTC {hour}:xx)")
            print(f"   價格: ${row['close']:.2f}")
        else:
            near_misses += 1
            print(f"\n⚠️  接近 SHORT 信號 (EMA未突破)")
            print(f"   時間: {row['timestamp']}")
            print(f"   價格: ${row['close']:.2f}, EMA200: ${row['ema_200']:.2f}")
            print(f"   差距: ${row['close'] - row['ema_200']:.2f}")

print("\n" + "=" * 70)
print("📋 總結")
print("=" * 70)
print(f"\n✅ 有效信號: {signals_found}")
print(f"⚠️  接近但未達標: {near_misses}")

if signals_found == 0:
    print("\n💡 分析：")
    print("  - 雖然有波動，但未同時滿足所有條件")
    print("  - 可能原因：時段不對、EMA200 未突破、或無明顯掃蕩")
    print("  - 建議：可考慮調整時段限制或 EMA 參數")
