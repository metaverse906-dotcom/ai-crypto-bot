# config/symbols.py
"""
多幣種監控配置
使用動態市值選擇（延遲載入，提升啟動速度）
"""
from config.symbols_extended import (
    LAZY_LOAD,
    USE_DYNAMIC_SELECTION,
    get_dynamic_symbols,
    get_static_symbols
)

# 延遲載入：啟動時不執行，第一次使用時才載入
if LAZY_LOAD and USE_DYNAMIC_SELECTION:
    # 暫時使用靜態列表，實際使用時才切換
    HYBRID_SFP_SYMBOLS = None  # 將在第一次訪問時載入
    _symbols_loaded = False
    
    def get_symbols():
        """延遲載入幣種列表"""
        global HYBRID_SFP_SYMBOLS, _symbols_loaded
        if not _symbols_loaded:
            HYBRID_SFP_SYMBOLS = get_dynamic_symbols(silent=True)
            _symbols_loaded = True
        return HYBRID_SFP_SYMBOLS
else:
    # 立即載入
    HYBRID_SFP_SYMBOLS = get_dynamic_symbols(silent=False) if USE_DYNAMIC_SELECTION else get_static_symbols()
    get_symbols = lambda: HYBRID_SFP_SYMBOLS

# 風險控制參數
MAX_CONCURRENT_POSITIONS = 3  # 最多同時持有 3 個倉位
MAX_PER_SYMBOL = 1             # 單一幣種最多 1 個倉位
POSITION_SIZE_PCT = 0.02       # 每筆交易 2% 倉位

# 策略參數
STRATEGY_TIMEFRAME = '4h'      # 時間框架
SCAN_INTERVAL_SECONDS = 3600   # 掃描間隔（1小時）

# 記錄配置
print(f"多幣種配置已載入：{len(HYBRID_SFP_SYMBOLS)} 個幣種")
for symbol in HYBRID_SFP_SYMBOLS:
    print(f"  - {symbol}")
