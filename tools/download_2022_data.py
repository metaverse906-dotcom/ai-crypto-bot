#!/usr/bin/env python3
# tools/download_2022_data.py
"""
下載2022年BTC數據供熊市回測
"""

import ccxt
import pandas as pd
from datetime import datetime
import time

def download_2022_data():
    """下載2022全年數據"""
    exchange = ccxt.binance()
    
    # 2022年時間範圍
    start = datetime(2022, 1, 1)
    end = datetime(2023, 1, 1)
    
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    
    print(f"下載2022年數據：{start} 到 {end}")
    print("使用1h K線...")
    
    all_data = []
    current_ms = start_ms
    
    while current_ms < end_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(
                'BTC/USDT',
                '1h',
                since=current_ms,
                limit=1000
            )
            
            if not ohlcv:
                break
            
            all_data.extend(ohlcv)
            current_ms = ohlcv[-1][0] + 3600000
            
            print(f"已下載 {len(all_data)} 根K線...", end='\r')
            time.sleep(0.5)
            
        except Exception as e:
            print(f"\n錯誤: {e}")
            time.sleep(2)
    
    # 轉換為DataFrame
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 去重
    df = df.drop_duplicates(subset=['timestamp'])
    
    # 保存
    output_file = 'data/backtest/BTC_USDT_1h_2022.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ 完成！")
    print(f"檔案: {output_file}")
    print(f"數量: {len(df)} 根K線")
    print(f"期間: {df.iloc[0]['timestamp']} 到 {df.iloc[-1]['timestamp']}")
    print(f"價格範圍: ${df['low'].min():.0f} - ${df['high'].max():.0f}")


if __name__ == "__main__":
    download_2022_data()
