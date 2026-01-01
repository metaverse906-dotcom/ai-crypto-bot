"""
DCA Strategy Configuration
定期定額投資策略配置
"""
from dataclasses import dataclass


@dataclass
class DCAConfig:
    """DCA 策略配置參數"""
    
    # ===== 基礎金額 =====
    base_amount_usd: float = 250.0  # 每週基礎投資金額（美元）
    
    # ===== Fear & Greed 閾值 =====
    fg_extreme_panic: int = 10      # 極度恐慌（4x）
    fg_strong_panic: int = 20       # 強烈恐慌（3x）
    fg_panic: int = 30              # 市場恐慌（2x）
    
    # ===== RSI 閾值 =====
    rsi_period: int = 14            # RSI 週期
    rsi_extreme_oversold: float = 25.0  # 極度超賣
    rsi_oversold: float = 30.0      # 超賣
    rsi_overbought: float = 70.0    # 超買
    
    # ===== 移動平均 =====
    ma_period: int = 200            # MA 週期
    
    # ===== 買入倍數 =====
    multiplier_extreme: float = 4.0  # 極度恐慌倍數
    multiplier_strong: float = 3.0   # 強烈恐慌倍數
    multiplier_panic: float = 2.0    # 市場恐慌倍數
    multiplier_rsi: float = 1.5      # RSI 恐慌倍數
    multiplier_normal: float = 1.0   # 正常倍數
    
    # ===== API 設定 =====
    fear_greed_api: str = "https://api.alternative.me/fng/"
    exchange_rate_api: str = "https://api.exchangerate-api.com/v4/latest/USD"
    default_usd_twd: float = 31.0   # 備用匯率
    
    # ===== 數據設定 =====
    ohlcv_limit: int = 201          # K 線數量（需要 200 + 1 用於移除未收盤）
    api_timeout: int = 10           # API 超時（秒）
    
    # ===== 快取設定 =====
    enable_cache: bool = True       # 啟用數據快取
    cache_ttl: int = 300            # 快取有效期（秒）


# 全局配置實例
config = DCAConfig()
