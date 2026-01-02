"""
策略配置中心

管理 DCA 策略模式選擇與參數
"""
import os
from dotenv import load_dotenv

load_dotenv()


class StrategyConfig:
    """策略配置類"""
    
    # ========== 策略模式選擇 ==========
    # 可選值：'FG' (Fear & Greed) 或 'MVRV' (MVRV-based)
    STRATEGY_MODE = os.getenv('STRATEGY_MODE', 'FG')  # 預設保持現有 F&G 策略
    
    # ========== MVRV 策略參數 ==========
    # 核心倉比例（只在 MVRV 模式使用）
    MVRV_CORE_RATIO = float(os.getenv('MVRV_CORE_RATIO', '0.4'))  # 預設 40%
    
    # MVRV 閾值設定
    MVRV_THRESHOLDS = {
        'extreme_low': 0.1,    # 極度低估
        'low': 1.0,            # 積累區
        'normal': 5.0,         # 正常上限
        'high': 6.0,           # 開始過熱
        'very_high': 7.0,      # 極度過熱  
        'extreme_high': 9.0    # 泡沫區
    }
    
    # ========== 共用參數 ==========
    BASE_WEEKLY_USD = float(os.getenv('BASE_WEEKLY_USD', '250'))  # 基礎每週投入
    
    # ========== 倉位管理 ==========
    # 倉位數據存儲路徑
    POSITION_DATA_FILE = os.getenv('POSITION_DATA_FILE', 'data/positions.json')
    
    @classmethod
    def is_mvrv_mode(cls) -> bool:
        """檢查是否為 MVRV 模式"""
        return cls.STRATEGY_MODE.upper() == 'MVRV'
    
    @classmethod
    def is_fg_mode(cls) -> bool:
        """檢查是否為 F&G 模式"""
        return cls.STRATEGY_MODE.upper() == 'FG'
    
    @classmethod
    def get_summary(cls) -> str:
        """獲取配置摘要"""
        return f"""
策略模式：{cls.STRATEGY_MODE}
基礎投入：${cls.BASE_WEEKLY_USD} USD/週
{'核心倉比例：' + f'{cls.MVRV_CORE_RATIO*100:.0f}%' if cls.is_mvrv_mode() else ''}
        """.strip()


# 全域實例
strategy_config = StrategyConfig()
