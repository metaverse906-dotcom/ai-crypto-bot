#!/usr/bin/env python3
# scripts/backtests/download_altcoin_data.py
"""
下載山寨幣回測所需的歷史數據

數據源:
- BTC Dominance: Coinranking API
- ETH/BTC Ratio: CoinGecko API
- ADA/SNEK Price: CoinGecko API
- Altcoin Season Index: 自行計算
"""

import httpx
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import time
from pathlib import Path

# 創建數據目錄
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class AltcoinDataDownloader:
    """山寨幣數據下載器"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
    
    async def download_btc_dominance(self, start_date: str, end_date: str):
        """
        下載 BTC Dominance 歷史數據
        
        Args:
            start_date: 開始日期 "2020-01-01"
            end_date: 結束日期 "2024-12-31"
        """
        print("📊 下載 BTC Dominance 數據...")
        
        url = "https://api.coinranking.com/v2/stats/bitcoin-dominance-history"
        
        # 轉換為 UNIX timestamp
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
        
        try:
            response = await self.session.get(url, params={
                "timePeriod": "1d",
                "from": start_ts,
                "to": end_ts
            })
            
            data = response.json()
            
            if 'data' in data and 'history' in data['data']:
                df = pd.DataFrame(data['data']['history'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.rename(columns={'timestamp': 'date', 'dominance': 'btc_dominance'})
                df = df[['date', 'btc_dominance']]
                
                # 保存
                output_file = DATA_DIR / "btc_dominance.csv"
                df.to_csv(output_file, index=False)
                print(f"✅ BTC Dominance 已保存: {len(df)} 筆數據 → {output_file}")
                return df
            else:
                print(f"⚠️ BTC Dominance API 回應異常: {data}")
                return None
                
        except Exception as e:
            print(f"❌ 下載 BTC Dominance 失敗: {e}")
            return None
    
    async def download_eth_btc_ratio(self, start_date: str, end_date: str):
        """下載 ETH/BTC 匯率歷史"""
        print("📊 下載 ETH/BTC 比率數據...")
        
        url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range"
        
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
        
        try:
            response = await self.session.get(url, params={
                "vs_currency": "btc",
                "from": start_ts,
                "to": end_ts
            })
            
            data = response.json()
            
            if 'prices' in data:
                df = pd.DataFrame(data['prices'], columns=['timestamp', 'eth_btc_ratio'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df[['date', 'eth_btc_ratio']]
                
                # 每日數據（取平均）
                df = df.groupby(df['date'].dt.date).mean().reset_index()
                
                output_file = DATA_DIR / "eth_btc_ratio.csv"
                df.to_csv(output_file, index=False)
                print(f"✅ ETH/BTC 已保存: {len(df)} 筆數據 → {output_file}")
                return df
            else:
                print(f"⚠️ ETH/BTC API 回應異常")
                return None
                
        except Exception as e:
            print(f"❌ 下載 ETH/BTC 失敗: {e}")
            # CoinGecko 免費版有 rate limit，等待後重試
            print("⏳ 等待 60 秒後重試...")
            await asyncio.sleep(60)
            return await self.download_eth_btc_ratio(start_date, end_date)
    
    async def download_coin_price(self, coin_id: str, start_date: str, end_date: str):
        """
        下載特定幣種價格
        
        Args:
            coin_id: CoinGecko ID (例如: "cardano", "snek")
            start_date: 開始日期
            end_date: 結束日期
        """
        print(f"📊 下載 {coin_id.upper()} 價格數據...")
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
        
        try:
            response = await self.session.get(url, params={
                "vs_currency": "usd",
                "from": start_ts,
                "to": end_ts
            })
            
            data = response.json()
            
            if 'prices' in data:
                df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df[['date', 'price']]
                
                # 每日數據（取收盤價，即最後一個）
                df = df.groupby(df['date'].dt.date).last().reset_index()
                
                output_file = DATA_DIR / f"{coin_id}_price.csv"
                df.to_csv(output_file, index=False)
                print(f"✅ {coin_id.upper()} 已保存: {len(df)} 筆數據 → {output_file}")
                return df
            else:
                print(f"⚠️ {coin_id} API 回應異常")
                return None
                
        except Exception as e:
            print(f"❌ 下載 {coin_id} 失敗: {e}")
            # Rate limit 處理
            print("⏳ 等待 60 秒後重試...")
            await asyncio.sleep(60)
            return await self.download_coin_price(coin_id, start_date, end_date)
    
    async def calculate_altseason_index(self, date: str):
        """
        計算特定日期的 Altcoin Season Index
        
        定義: 過去 90 天內，前 50 大幣種中有多少百分比跑贏 BTC
        
        Note: 這需要大量 API 調用，建議分批處理
        """
        # TODO: 實作完整的 Altseason Index 計算
        # 暫時先下載主要數據
        pass
    
    async def close(self):
        """關閉 HTTP 連接"""
        await self.session.aclose()


async def main():
    """主程式"""
    print("=" * 60)
    print("山寨幣回測數據下載工具")
    print("=" * 60)
    
    # 設定日期範圍
    start_date = "2020-01-01"
    end_date = "2024-12-31"
    
    print(f"\n📅 數據範圍: {start_date} ~ {end_date}\n")
    
    downloader = AltcoinDataDownloader()
    
    try:
        # 1. BTC Dominance
        await downloader.download_btc_dominance(start_date, end_date)
        await asyncio.sleep(2)  # 避免 rate limit
        
        # 2. ETH/BTC Ratio
        await downloader.download_eth_btc_ratio(start_date, end_date)
        await asyncio.sleep(2)
        
        # 3. ADA Price (2020-2024)
        await downloader.download_coin_price("cardano", start_date, end_date)
        await asyncio.sleep(2)
        
        # 4. SNEK Price (2023起，SNEK 2023年4月上市)
        snek_start = "2023-04-01"
        await downloader.download_coin_price("snek", snek_start, end_date)
        
        print("\n" + "=" * 60)
        print("✅ 所有數據下載完成！")
        print(f"📁 數據位置: {DATA_DIR}")
        print("=" * 60)
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())
