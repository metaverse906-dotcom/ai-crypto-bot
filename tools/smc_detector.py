#!/usr/bin/env python3
# tools/smc_detector.py
"""
SMC (Smart Money Concepts) 偵測器
- Order Block 偵測
- Fair Value Gap (FVG) 偵測
- Break of Structure (BOS) 識別
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class SMCDetector:
    """
    Smart Money Concepts 偵測器
    用於識別機構交易行為的價格結構
    """
    
    def __init__(self, atr_multiplier: float = 1.5, lookback: int = 20):
        """
        Args:
            atr_multiplier: ATR 倍數，用於判斷強勢 K 線
            lookback: 回看週期，用於 BOS 判斷
        """
        self.atr_multiplier = atr_multiplier
        self.lookback = lookback
        
        # 儲存偵測結果
        self.order_blocks: List[Dict] = []
        self.fvgs: List[Dict] = []
    
    # ==================== Order Block 偵測 ====================
    
    def detect_order_block(self, df: pd.DataFrame, i: int) -> Optional[Dict]:
        """
        偵測 Order Block（訂單塊）
        
        邏輯：
        1. 找到強勢反轉 K 線（實體 > 1.5x ATR）
        2. 該 K 線後價格朝反方向移動
        3. 訂單塊區域 = K 線實體範圍
        
        Args:
            df: K線數據（需包含 atr 欄位）
            i: 當前 K 線索引
            
        Returns:
            Order Block 字典或 None
        """
        if i >= len(df) - 5:
            return None
        
        candle = df.iloc[i]
        future = df.iloc[i+1:i+5]
        
        # 確保有 ATR 數據
        if pd.isna(candle.get('atr')):
            return None
        
        atr = candle['atr']
        body_size = abs(candle['close'] - candle['open'])
        
        # 檢查是否為強勢 K 線
        if body_size < self.atr_multiplier * atr:
            return None
        
        # Bullish Order Block（看漲訂單塊）
        # 條件：大陰線後價格反轉向上
        if candle['close'] < candle['open']:  # 陰線
            # 檢查後續 K 線是否都在低點之上（反轉向上）
            if len(future) > 0 and future['close'].min() > candle['low']:
                return {
                    'type': 'BULLISH_OB',
                    'zone_low': candle['low'],
                    'zone_high': candle['open'],
                    'timestamp': candle['timestamp'],
                    'strength': body_size / atr  # 強度評分
                }
        
        # Bearish Order Block（看跌訂單塊）
        # 條件：大陽線後價格反轉向下
        elif candle['close'] > candle['open']:  # 陽線
            if len(future) > 0 and future['close'].max() < candle['high']:
                return {
                    'type': 'BEARISH_OB',
                    'zone_low': candle['close'],
                    'zone_high': candle['high'],
                    'timestamp': candle['timestamp'],
                    'strength': body_size / atr
                }
        
        return None
    
    # ==================== Fair Value Gap 偵測 ====================
    
    def detect_fvg(self, df: pd.DataFrame, i: int) -> Optional[Dict]:
        """
        偵測 Fair Value Gap（公允價值缺口）
        
        邏輯：
        - Bullish FVG: K1.high < K3.low（中間有缺口）
        - Bearish FVG: K1.low > K3.high
        
        Args:
            df: K線數據
            i: 當前 K 線索引（至少需要 i >= 2）
            
        Returns:
            FVG 字典或 None
        """
        if i < 2:
            return None
        
        k1 = df.iloc[i-2]
        k2 = df.iloc[i-1]
        k3 = df.iloc[i]
        
        # Bullish FVG（向上缺口）
        if k1['high'] < k3['low']:
            gap_size = k3['low'] - k1['high']
            return {
                'type': 'BULLISH_FVG',
                'gap_low': k1['high'],
                'gap_high': k3['low'],
                'size': gap_size,
                'timestamp': k3['timestamp']
            }
        
        # Bearish FVG（向下缺口）
        if k1['low'] > k3['high']:
            gap_size = k1['low'] - k3['high']
            return {
                'type': 'BEARISH_FVG',
                'gap_low': k3['high'],
                'gap_high': k1['low'],
                'size': gap_size,
                'timestamp': k3['timestamp']
            }
        
        return None
    
    # ==================== Break of Structure 識別 ====================
    
    def detect_bos(self, df: pd.DataFrame) -> Optional[str]:
        """
        偵測 Break of Structure（結構突破）
        
        邏輯：
        - Bullish BOS: 突破前期高點
        - Bearish BOS: 跌破前期低點
        
        Args:
            df: K線數據
            
        Returns:
            'BULLISH_BOS', 'BEARISH_BOS' 或 None
        """
        if len(df) < self.lookback + 1:
            return None
        
        # 計算前期高低點
        recent = df.tail(self.lookback + 1)
        prev_high = recent['high'].iloc[:-1].max()
        prev_low = recent['low'].iloc[:-1].min()
        
        current = recent.iloc[-1]
        
        # Bullish BOS（突破前期高點）
        if current['high'] > prev_high:
            return 'BULLISH_BOS'
        
        # Bearish BOS（跌破前期低點）
        if current['low'] < prev_low:
            return 'BEARISH_BOS'
        
        return None
    
    # ==================== 整合掃描 ====================
    
    def scan(self, df: pd.DataFrame):
        """
        掃描整個數據集，偵測所有 SMC 結構
        
        Args:
            df: K線數據
        """
        self.order_blocks = []
        self.fvgs = []
        
        # 掃描 Order Blocks
        for i in range(len(df) - 5):
            ob = self.detect_order_block(df, i)
            if ob:
                self.order_blocks.append(ob)
        
        # 掃描 FVGs
        for i in range(2, len(df)):
            fvg = self.detect_fvg(df, i)
            if fvg:
                self.fvgs.append(fvg)
    
    # ==================== 輔助判斷函數 ====================
    
    def check_ob_confluence(self, price: float, direction: str, recent_only: bool = True) -> bool:
        """
        檢查價格是否在 Order Block 支持區域內
        
        Args:
            price: 當前價格
            direction: 'LONG' 或 'SHORT'
            recent_only: 是否只考慮最近的 OB（最近 50 根 K 線內）
            
        Returns:
            是否有 Order Block 支持
        """
        if not self.order_blocks:
            return False
        
        # 如果只看最近的，取最後 50 個
        obs = self.order_blocks[-50:] if recent_only else self.order_blocks
        
        for ob in obs:
            if direction == 'LONG' and ob['type'] == 'BULLISH_OB':
                # 價格在看漲 OB 區域內
                if ob['zone_low'] <= price <= ob['zone_high']:
                    return True
            
            elif direction == 'SHORT' and ob['type'] == 'BEARISH_OB':
                # 價格在看跌 OB 區域內
                if ob['zone_low'] <= price <= ob['zone_high']:
                    return True
        
        return False
    
    def get_nearest_ob(self, price: float, direction: str) -> Optional[Dict]:
        """
        獲取最近的 Order Block
        
        Args:
            price: 當前價格
            direction: 'LONG' 或 'SHORT'
            
        Returns:
            最近的 Order Block 或 None
        """
        if not self.order_blocks:
            return None
        
        # 過濾符合方向的 OB
        if direction == 'LONG':
            valid_obs = [ob for ob in self.order_blocks if ob['type'] == 'BULLISH_OB']
        else:
            valid_obs = [ob for ob in self.order_blocks if ob['type'] == 'BEARISH_OB']
        
        if not valid_obs:
            return None
        
        # 找到最近的（距離當前價格最近）
        nearest = min(valid_obs, key=lambda ob: abs(price - (ob['zone_low'] + ob['zone_high']) / 2))
        return nearest
    
    def get_summary(self) -> Dict:
        """
        獲取 SMC 偵測摘要
        
        Returns:
            包含統計信息的字典
        """
        return {
            'total_order_blocks': len(self.order_blocks),
            'bullish_obs': len([ob for ob in self.order_blocks if ob['type'] == 'BULLISH_OB']),
            'bearish_obs': len([ob for ob in self.order_blocks if ob['type'] == 'BEARISH_OB']),
            'total_fvgs': len(self.fvgs),
            'bullish_fvgs': len([fvg for fvg in self.fvgs if fvg['type'] == 'BULLISH_FVG']),
            'bearish_fvgs': len([fvg for fvg in self.fvgs if fvg['type'] == 'BEARISH_FVG'])
        }


# ==================== 測試函數 ====================

def test_smc_detector():
    """測試 SMC 偵測器"""
    import pandas_ta as ta
    
    print("🧪 測試 SMC 偵測器\n")
    
    # 生成模擬數據
    import ccxt
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '15m', limit=500)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 計算 ATR
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # 初始化偵測器
    detector = SMCDetector()
    
    # 掃描
    print("📊 掃描 Order Blocks 和 FVGs...")
    detector.scan(df)
    
    # 顯示結果
    summary = detector.get_summary()
    print(f"\n✅ 掃描完成！")
    print(f"   Order Blocks: {summary['total_order_blocks']} 個")
    print(f"     - 看漲: {summary['bullish_obs']}")
    print(f"     - 看跌: {summary['bearish_obs']}")
    print(f"   FVGs: {summary['total_fvgs']} 個")
    print(f"     - 看漲: {summary['bullish_fvgs']}")
    print(f"     - 看跌: {summary['bearish_fvgs']}")
    
    # 測試 BOS
    bos = detector.detect_bos(df)
    print(f"\n   當前 BOS: {bos if bos else '無'}")
    
    # 測試價格支持
    current_price = df['close'].iloc[-1]
    long_support = detector.check_ob_confluence(current_price, 'LONG')
    short_support = detector.check_ob_confluence(current_price, 'SHORT')
    
    print(f"\n   當前價格: ${current_price:.2f}")
    print(f"   LONG Order Block 支持: {'✅' if long_support else '❌'}")
    print(f"   SHORT Order Block 支持: {'✅' if short_support else '❌'}")


if __name__ == "__main__":
    test_smc_detector()
