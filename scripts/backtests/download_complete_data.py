#!/usr/bin/env python3
# scripts/backtests/download_complete_data.py
"""
下載完整 4 年歷史數據（2020-2024）
使用 CCXT 和公開數據源
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import sys

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def download_complete_ohlcv(symbol: str, start_date: str = "2020-01-01", exchange_name: str = "binance"):
    """
    下載完整 OHLCV 數據
    
    Args:
        symbol: 交易對，例如 'ADA/USDT'
        start_date: 開始日期 'YYYY-MM-DD'
        exchange_name: 交易所名稱
    """
    print(f"\n📊 下載 {symbol} 完整歷史數據...")
    print(f"   交易所: {exchange_name}")
    print(f"   開始日期: {start_date}")
    
    # 初始化交易所
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class({'enableRateLimit': True})
    
    # 轉換日期
    since = exchange.parse8601(f'{start_date}T00:00:00Z')
    now = exchange.milliseconds()
    
    all_data = []
    current_since = since
    
    try:
        while current_since < now:
            # 下載數據
            ohlcv = exchange.fetch_ohlcv(
                symbol, 
                timeframe='1d',
                since=current_since,
                limit=1000
            )
            
            if not ohlcv:
                break
            
            all_data.extend(ohlcv)
            
            # 更新時間戳
            current_since = ohlcv[-1][0] + 86400000  # 下一天
            
            print(f"   已下載 {len(all_data)} 天數據...", end='\r')
            
            # 遵守 rate limit
            time.sleep(exchange.rateLimit / 1000)
            
            # 如果返回少於 1000 筆，表示沒有更多數據
            if len(ohlcv) < 1000:
                break
        
        print(f"\n   ✅ 完成！總共 {len(all_data)} 天")
        
        # 轉換為 DataFrame
        df = pd.DataFrame(
            all_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 去重並排序
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        return df
        
    except Exception as e:
        print(f"\n   ❌ 錯誤: {e}")
        return None


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    計算技術指標
    
    Args:
        df: 包含 OHLCV 數據的 DataFrame
    
    Returns:
        添加了技術指標的 DataFrame
    """
    print("\n📈 計算技術指標...")
    
    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Moving Averages
    df['ma_7'] = df['close'].rolling(window=7).mean()
    df['ma_30'] = df['close'].rolling(window=30).mean()
    df['ma_200'] = df['close'].rolling(window=200).mean()
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    
    print("   ✅ RSI, MA, Bollinger Bands")
    
    return df


def main():
    """主程式"""
    print("=" * 70)
    print("下載完整 4 年歷史數據（2020-2024）")
    print("=" * 70)
    
    # 1. 下載 ADA
    print("\n[1/4] ADA/USDT")
    ada_df = download_complete_ohlcv('ADA/USDT', '2020-01-01', 'binance')
    
    if ada_df is not None:
        # 計算技術指標
        ada_df = calculate_technical_indicators(ada_df)
        
        # 保存完整數據（含技術指標）
        ada_df.to_csv(DATA_DIR / "ada_complete.csv", index=False)
        
        # 保存簡化版（只有價格）
        ada_simple = ada_df[['date', 'close']].rename(columns={'close': 'price'})
        ada_simple.to_csv(DATA_DIR / "cardano_price.csv", index=False)
        
        print(f"   💾 已保存: {len(ada_df)} 天")
        print(f"   📅 範圍: {ada_df['date'].min().date()} ~ {ada_df['date'].max().date()}")
    
    # 2. 下載 BTC
    print("\n[2/4] BTC/USDT")
    btc_df = download_complete_ohlcv('BTC/USDT', '2020-01-01', 'binance')
    
    if btc_df is not None:
        btc_df = calculate_technical_indicators(btc_df)
        btc_df.to_csv(DATA_DIR / "btc_complete.csv", index=False)
        
        btc_simple = btc_df[['date', 'close']].rename(columns={'close': 'price'})
        btc_simple.to_csv(DATA_DIR / "bitcoin_price.csv", index=False)
        
        print(f"   💾 已保存: {len(btc_df)} 天")
    
    # 3. 下載 ETH
    print("\n[3/4] ETH/USDT")
    eth_df = download_complete_ohlcv('ETH/USDT', '2020-01-01', 'binance')
    
    if eth_df is not None:
        eth_df = calculate_technical_indicators(eth_df)
        eth_df.to_csv(DATA_DIR / "eth_complete.csv", index=False)
        
        eth_simple = eth_df[['date', 'close']].rename(columns={'close': 'price'})
        eth_simple.to_csv(DATA_DIR / "ethereum_price.csv", index=False)
        
        print(f"   💾 已保存: {len(eth_df)} 天")
    
    # 4. 計算 ETH/BTC 比率
    if btc_df is not None and eth_df is not None:
        print("\n[4/4] 計算 ETH/BTC 比率")
        
        merged = pd.merge(
            btc_df[['date', 'close']].rename(columns={'close': 'btc_price'}),
            eth_df[['date', 'close']].rename(columns={'close': 'eth_price'}),
            on='date'
        )
        
        merged['eth_btc_ratio'] = merged['eth_price'] / merged['btc_price']
        eth_btc = merged[['date', 'eth_btc_ratio']]
        
        eth_btc.to_csv(DATA_DIR / "eth_btc_ratio.csv", index=False)
        print(f"   💾 已保存: {len(eth_btc)} 天")
    
    print("\n" + "=" * 70)
    print("✅ 所有數據下載完成！")
    print(f"📁 位置: {DATA_DIR}")
    print("=" * 70)
    
    # 顯示統計
    if ada_df is not None:
        print(f"\n📊 ADA 數據統計:")
        print(f"   天數: {len(ada_df)}")
        print(f"   最高價: ${ada_df['high'].max():.4f}")
        print(f"   最低價: ${ada_df['low'].min():.4f}")
        print(f"   當前價: ${ada_df['close'].iloc[-1]:.4f}")


if __name__ == "__main__":
    main()
