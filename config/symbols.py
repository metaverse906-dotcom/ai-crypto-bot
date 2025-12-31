# config/symbols.py
"""
多幣種監控配置（簡化版，與 VM 同步）
"""

# 靜態列表（13 個幣種）
HYBRID_SFP_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT',
    'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
    'UNI/USDT', 'ATOM/USDT', 'LTC/USDT'
]

def get_symbols():
    """返回幣種列表"""
    return HYBRID_SFP_SYMBOLS

# 風險控制參數
MAX_CONCURRENT_POSITIONS = 3
MAX_PER_SYMBOL = 1
POSITION_SIZE_PCT = 0.02
