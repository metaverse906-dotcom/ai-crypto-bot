# core/risk_manager.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class RiskManager:
    """風險管理系統 - 相關性管理 + 市場狀態識別 + 動態風險分配"""
    
    def __init__(self, execution_system):
        self.exec = execution_system
        
        # 風險參數
        self.base_risk_per_trade = 0.02  # 基礎風險 2%
        self.max_correlation = 0.8        # 最大容忍相關性
        
        # 快取
        self.correlation_cache = {}       # {(symbol1, symbol2): correlation}
        self.market_regime = 'SIDEWAYS'   # BULL/BEAR/SIDEWAYS
        self.regime_update_time = None
        
    async def calculate_correlation(self, symbol1, symbol2, days=30):
        """
        計算兩個資產的滾動相關性
        Returns: float (-1 to 1)
        """
        # 檢查快取
        cache_key = tuple(sorted([symbol1, symbol2]))
        if cache_key in self.correlation_cache:
            return self.correlation_cache[cache_key]
        
        try:
            # 獲取歷史數據
            df1 = await self.exec.fetch_ohlcv_for_symbol(symbol1, '1d', limit=days)
            df2 = await self.exec.fetch_ohlcv_for_symbol(symbol2, '1d', limit=days)
            
            if df1 is None or df2 is None or len(df1) < 10 or len(df2) < 10:
                return 0.0  # 數據不足，假設無相關
            
            # 計算收益率
            returns1 = df1['close'].pct_change().dropna()
            returns2 = df2['close'].pct_change().dropna()
            
            # 對齊時間序列
            min_len = min(len(returns1), len(returns2))
            returns1 = returns1.iloc[-min_len:]
            returns2 = returns2.iloc[-min_len:]
            
            # 計算 Pearson 相關係數
            correlation = returns1.corr(returns2)
            
            # 快取結果（1小時有效）
            self.correlation_cache[cache_key] = correlation
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            print(f"⚠️ 相關性計算失敗: {e}")
            return 0.0
    
    async def check_correlation_risk(self, new_symbol, active_positions):
        """
        檢查新倉位是否與現有倉位高度相關
        Returns: {'approved': bool, 'reason': str, 'risk_penalty': float}
        """
        if not active_positions:
            return {'approved': True, 'risk_penalty': 1.0}
        
        # 提取活躍倉位的幣種
        active_symbols = list(set([pos['symbol'] for pos in active_positions]))
        
        # 計算與所有活躍倉位的相關性
        correlations = {}
        for active_symbol in active_symbols:
            if active_symbol == new_symbol:
                continue  # 跳過自己
            
            corr = await self.calculate_correlation(new_symbol, active_symbol)
            correlations[active_symbol] = corr
        
        # 找出最高相關性
        if correlations:
            max_corr_symbol = max(correlations, key=correlations.get)
            max_corr = correlations[max_corr_symbol]
            
            if max_corr > self.max_correlation:
                return {
                    'approved': False,
                    'reason': f'與 {max_corr_symbol} 相關性過高 ({max_corr:.2f})',
                    'risk_penalty': 0.5
                }
            elif max_corr > 0.6:
                # 中度相關，降低風險
                return {
                    'approved': True,
                    'reason': f'與 {max_corr_symbol} 中度相關 ({max_corr:.2f})，降低倉位',
                    'risk_penalty': 0.7
                }
        
        return {'approved': True, 'risk_penalty': 1.0}
    
    async def detect_market_regime(self):
        """
        識別市場狀態 (BULL/BEAR/SIDEWAYS)
        每小時更新一次即可
        Returns: str
        """
        # 檢查是否需要更新（1小時內不重複計算）
        if self.regime_update_time:
            if (datetime.now() - self.regime_update_time).seconds < 3600:
                return self.market_regime
        
        try:
            # 獲取 BTC 日線數據
            btc_df = await self.exec.fetch_ohlcv_for_symbol('BTC/USDT', '1d', limit=200)
            
            if btc_df is None or len(btc_df) < 200:
                return 'SIDEWAYS'  # 默認震盪
            
            # 計算 MA(50) & MA(200)
            ma_50 = btc_df['close'].rolling(50).mean().iloc[-1]
            ma_200 = btc_df['close'].rolling(200).mean().iloc[-1]
            
            # 計算 7 日漲跌幅
            week_change = (btc_df['close'].iloc[-1] / btc_df['close'].iloc[-7] - 1) * 100
            
            # 判斷邏輯
            if ma_50 > ma_200 and week_change > 5:
                regime = 'BULL'
            elif ma_50 < ma_200 and week_change < -5:
                regime = 'BEAR'
            else:
                regime = 'SIDEWAYS'
            
            self.market_regime = regime
            self.regime_update_time = datetime.now()
            
            return regime
            
        except Exception as e:
            print(f"⚠️ 市場狀態識別失敗: {e}")
            return 'SIDEWAYS'
    
    async def get_dynamic_risk(self, base_risk=None, ai_confidence=None):
        """
        動態計算風險預算
        考慮：市場環境 + AI 信心度
        Returns: float (調整後的風險比例)
        """
        if base_risk is None:
            base_risk = self.base_risk_per_trade
        
        # 1. 市場環境調整
        regime = await self.detect_market_regime()
        regime_multiplier = {
            'BULL': 1.3,      # 牛市：加倉
            'BEAR': 0.6,      # 熊市：減倉
            'SIDEWAYS': 1.0   # 震盪：正常
        }[regime]
        
        # 2. AI 信心度調整
        confidence_multiplier = 1.0
        if ai_confidence is not None:
            if ai_confidence > 0.8:
                confidence_multiplier = 1.2  # 高信心加倉
            elif ai_confidence < 0.5:
                confidence_multiplier = 0.7  # 低信心減倉
        
        # 綜合調整
        adjusted_risk = base_risk * regime_multiplier * confidence_multiplier
        
        # 上下限保護
        adjusted_risk = max(0.01, min(0.04, adjusted_risk))  # 1%-4% 之間
        
        return adjusted_risk
