#!/usr/bin/env python3
"""
動態幣種選擇器（根據市值自動更新）
使用 CoinGecko API 獲取即時市值排名
"""
import requests
import json
from datetime import datetime, timedelta
import os

class DynamicSymbolSelector:
    def __init__(self, config_file='data/symbol_selector_cache.json'):
        self.config_file = config_file
        self.cache_duration = 168  # 小時（每週更新一次 = 7天）
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        
    def get_top_symbols(self, top_n=15, exclude=['USDT', 'USDC', 'BUSD', 'DAI'], verbose=False):
        """
        獲取市值前 N 名幣種（排除穩定幣）
        
        Args:
            top_n: 要獲取的幣種數量
            exclude: 排除的幣種（穩定幣）
            verbose: 是否顯示詳細訊息
            
        Returns:
            list: 幣種列表（格式：['BTC/USDT', 'ETH/USDT', ...]）
        """
        # 檢查快取
        if self._is_cache_valid():
            if verbose:
                print("使用快取的市值排名...")
            return self._load_cache()
        
        if verbose:
            print("從 CoinGecko 獲取最新市值排名...")
        
        try:
            # CoinGecko API: 獲取市值排名
            url = f"{self.coingecko_api}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': top_n + 20,  # 多取一些，過濾後才夠
                'page': 1,
                'sparkline': False
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 過濾並轉換
            symbols = []
            for coin in data:
                symbol = coin['symbol'].upper()
                
                # 排除穩定幣
                if symbol in exclude:
                    continue
                
                # 檢查 Binance 是否有此交易對
                binance_symbol = f"{symbol}/USDT"
                if self._check_binance_availability(binance_symbol):
                    symbols.append({
                        'symbol': binance_symbol,
                        'name': coin['name'],
                        'market_cap': coin['market_cap'],
                        'rank': coin['market_cap_rank']
                    })
                
                if len(symbols) >= top_n:
                    break
            
            # 儲存快取
            self._save_cache(symbols)
            
            if verbose:
                print(f"✅ 成功獲取 {len(symbols)} 個幣種")
            return [s['symbol'] for s in symbols]
            
        except Exception as e:
            if verbose:
                print(f"❌ 獲取市值排名失敗: {e}")
                print("使用預設幣種列表...")
            return self._get_fallback_symbols()
    
    def _check_binance_availability(self, symbol):
        """檢查幣種在 Binance 是否可交易"""
        try:
            import ccxt
            exchange = ccxt.binance()
            markets = exchange.load_markets()
            return symbol in markets
        except:
            # 如果檢查失敗，假設可用（降級處理）
            return True
    
    def _is_cache_valid(self):
        """檢查快取是否有效"""
        if not os.path.exists(self.config_file):
            return False
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cache_time = datetime.fromisoformat(data['updated_at'])
            age = datetime.now() - cache_time
            
            return age < timedelta(hours=self.cache_duration)
        except:
            return False
    
    def _load_cache(self):
        """載入快取"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [s['symbol'] for s in data['symbols']]
    
    def _save_cache(self, symbols):
        """儲存快取"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        data = {
            'updated_at': datetime.now().isoformat(),
            'symbols': symbols
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _get_fallback_symbols(self):
        """備用幣種列表（API 失敗時使用）"""
        return [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
            'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT',
            'UNI/USDT', 'ATOM/USDT', 'LTC/USDT'
        ]
    
    def print_current_selection(self):
        """顯示當前選擇的幣種"""
        if not os.path.exists(self.config_file):
            print("尚未載入市值排名")
            return
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n當前市值選擇（更新時間：{data['updated_at'][:19]}）")
        print("=" * 60)
        print(f"{'排名':<6} {'幣種':<12} {'名稱':<20} {'市值（USD）':<15}")
        print("-" * 60)
        
        for s in data['symbols']:
            market_cap = s['market_cap'] / 1e9  # 轉換為十億
            print(f"{s['rank']:<6} {s['symbol']:<12} {s['name']:<20} ${market_cap:,.2f}B")


# 使用範例
if __name__ == "__main__":
    selector = DynamicSymbolSelector()
    
    # 獲取市值前 13 名
    symbols = selector.get_top_symbols(top_n=13)
    
    # 顯示結果
    selector.print_current_selection()
    
    print(f"\n用於 Hybrid SFP 的幣種列表：")
    print(f"HYBRID_SFP_SYMBOLS = {symbols}")
