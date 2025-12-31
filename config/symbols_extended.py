# config/symbols_extended.py
"""
擴展多幣種監控配置（支援動態市值選擇）
可選模式：
1. 靜態模式：手動指定幣種
2. 動態模式：根據市值自動更新（延遲載入）
"""
import os
import sys

# 動態模式開關
USE_DYNAMIC_SELECTION = True  # 改成 False 使用靜態列表
DYNAMIC_TOP_N = 13  # 動態模式選擇前 N 名
LAZY_LOAD = True  # 延遲載入（啟動時不執行，第一次使用時才載入）

# 快取變數
_symbols_cache = None
_cache_loaded = False

def get_dynamic_symbols(silent=True):
    """
    取得動態市值選擇的幣種列表
    
    Args:
        silent: 是否靜默模式（不輸出大量訊息）
    
    Returns:
        幣種列表
    """
    global _symbols_cache, _cache_loaded
    
    # 使用快取
    if _cache_loaded and _symbols_cache is not None:
        return _symbols_cache
    
    try:
        # 載入動態選擇器
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from tools.dynamic_market_cap_selector import DynamicSymbolSelector
        
        selector = DynamicSymbolSelector()
        _symbols_cache = selector.get_top_symbols(top_n=DYNAMIC_TOP_N)
        _cache_loaded = True
        
        if not silent:
            print(f"✅ 動態市值模式已啟用（前 {DYNAMIC_TOP_N} 名）")
        
        return _symbols_cache
        
    except Exception as e:
        if not silent:
            print(f"⚠️ 動態選擇失敗（{e}），使用靜態列表")
        return get_static_symbols()

def get_static_symbols():
    """靜態幣種列表（備用）"""
    return [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT',
        'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
        'UNI/USDT', 'ATOM/USDT', 'LTC/USDT',
    ]


# 原始配置（保持不變）
HYBRID_SFP_SYMBOLS_ORIGINAL = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'SOL/USDT',
    'MATIC/USDT'
]

# 風險控制參數（不變）
MAX_CONCURRENT_POSITIONS = 3  # 最多同時持有 3 個倉位
MAX_PER_SYMBOL = 1             # 單一幣種最多 1 個倉位
POSITION_SIZE_PCT = 0.02       # 每筆交易 2% 倉位

# 策略參數（不變）
STRATEGY_TIMEFRAME = '4h'      # 時間框架
SCAN_INTERVAL_SECONDS = 3600   # 掃描間隔（1小時）

# 記錄配置
print(f"\n配置已載入：")
print(f"  原版：{len(HYBRID_SFP_SYMBOLS_ORIGINAL)} 個幣種")
print(f"  擴展版：{len(HYBRID_SFP_SYMBOLS_EXTENDED)} 個幣種")
print(f"\n擴展版幣種列表：")
for i, symbol in enumerate(HYBRID_SFP_SYMBOLS_EXTENDED, 1):
    print(f"  {i:2d}. {symbol}")
