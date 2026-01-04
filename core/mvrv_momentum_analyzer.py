# -*- coding: utf-8 -*-
"""
MVRV 動能分析模組（學術級）

實現基於研究報告的 MVRV Z-Score 動能檢測
使用 EMA 平滑和線性回歸斜率分析
"""

import numpy as np
from scipy import stats

class MVRVMomentumAnalyzer:
    """
    學術級 MVRV 動能分析器
    
    功能：
    - 14 日 EMA 平滑 MVRV Z-Score
    - 7 日線性回歸斜率計算
    - 三階段市場動能檢測
    - 動態 DCA Out 賣出比例計算
    """
    
    def __init__(self, ema_period=14, slope_period=7):
        """
        初始化分析器
        
        Args:
            ema_period: EMA 平滑週期（建議 14）
            slope_period: 斜率計算週期（建議 7）
        """
        self.ema_period = ema_period
        self.slope_period = slope_period
        self.z_history = []
        self.smoothed_z_history = []
        
        # 研究報告參數
        self.THRESHOLD_LOW = 1.5      # 啟動閾值
        self.THRESHOLD_HIGH = 3.0     # 高位閾值
        self.SLOPE_BULL = 0.05        # 快速上升閾值
        self.SLOPE_FLAT_POS = 0.03    # 高原期上界
        self.SLOPE_FLAT_NEG = -0.03   # 高原期下界
        self.SLOPE_BEAR = -0.05       # 下跌閾值
        
        # DCA Out 參數
        self.BASE_SELL_RATE = 0.005   # 基礎賣出率 0.5%
        self.Z_NORM = 2.0             # 標準化常數
    
    def update(self, current_mvrv):
        """
        更新 MVRV 值並分析
        
        Args:
            current_mvrv: 當前 MVRV Z-Score
            
        Returns:
            dict: 包含 phase, slope, smoothed_z, sell_percentage
        """
        self.z_history.append(current_mvrv)
        
        # 計算 EMA 平滑
        if len(self.z_history) >= 2:
            alpha = 2 / (self.ema_period + 1)
            if len(self.smoothed_z_history) == 0:
                smoothed = self.z_history[0]
            else:
                smoothed = alpha * current_mvrv + (1 - alpha) * self.smoothed_z_history[-1]
            self.smoothed_z_history.append(smoothed)
        else:
            self.smoothed_z_history.append(current_mvrv)
        
        return self.analyze()
    
    def calculate_slope(self):
        """計算線性回歸斜率"""
        if len(self.smoothed_z_history) < self.slope_period:
            return 0.0
        
        y = np.array(self.smoothed_z_history[-self.slope_period:])
        x = np.arange(len(y))
        
        try:
            slope, _, _, _, _ = stats.linregress(x, y)
            return slope
        except:
            return 0.0
    
    def analyze(self):
        """
        分析當前市場階段
        
        Returns:
            dict: {
                'phase': 階段名稱,
                'slope': 斜率值,
                'smoothed_z': 平滑後的 Z-Score,
                'sell_percentage': 建議賣出比例
            }
        """
        if len(self.smoothed_z_history) < self.slope_period:
            return {
                'phase': 'DATA_GATHERING',
                'slope': 0.0,
                'smoothed_z': 0.0,
                'sell_percentage': 0.0
            }
        
        smoothed_z = self.smoothed_z_history[-1]
        slope = self.calculate_slope()
        
        # 階段檢測
        phase = "NEUTRAL"
        momentum_multiplier = 0.0
        base_rate = 0.0
        
        # 過濾：只在 SZ > 閾值時啟動
        if smoothed_z < self.THRESHOLD_LOW:
            return {
                'phase': 'ACCUMULATION',
                'slope': slope,
                'smoothed_z': smoothed_z,
                'sell_percentage': 0.0
            }
        
        # 階段 1：快速上升
        if slope > self.SLOPE_BULL and smoothed_z > self.THRESHOLD_LOW:
            phase = "RAPID_ASCENT"
            momentum_multiplier = 0.5
            base_rate = 0.002  # 0.2%
        
        # 階段 2：高原期（關鍵賣出區）
        elif (self.SLOPE_FLAT_NEG <= slope <= self.SLOPE_FLAT_POS 
              and smoothed_z > self.THRESHOLD_HIGH):
            phase = "PLATEAU"
            momentum_multiplier = 2.5
            base_rate = 0.01  # 1.0%
        
        # 階段 3：下跌/反轉
        elif slope < self.SLOPE_BEAR:
            phase = "DECLINE"
            momentum_multiplier = 4.0
            base_rate = 0.01  # 1.0%
        
        else:
            phase = "TRANSITION"
            momentum_multiplier = 1.0
            base_rate = 0.005
        
        # 計算賣出比例
        # 公式：Sell% = Base_Rate × M_factor × (SZ_t / Z_norm)
        intensity_factor = smoothed_z / self.Z_NORM
        sell_percentage = base_rate * momentum_multiplier * intensity_factor
        
        # 安全上限：單次最多 10%
        sell_percentage = min(sell_percentage, 0.10)
        
        return {
            'phase': phase,
            'slope': slope,
            'smoothed_z': smoothed_z,
            'sell_percentage': sell_percentage
        }
