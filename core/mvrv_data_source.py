"""
MVRV Z-Score 數據源模組

提供比特幣鏈上估值指標：
- MVRV Z-Score (市值/已實現價值 Z 分數)
- Pi Cycle Top Indicator (111DMA vs 350DMA×2)
- 200週移動平均線
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import os
from dotenv import load_dotenv
from core.exchange_manager import get_exchange

load_dotenv()
logger = logging.getLogger(__name__)

# 快取設定
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_DURATION = timedelta(hours=24)


class MVRVDataError(Exception):
    """MVRV 數據獲取錯誤"""
    pass


def get_mvrv_z_score() -> Optional[float]:
    """
    獲取 MVRV Z-Score
    
    Returns:
        float: Z-Score 值，範圍通常在 -1 到 10
    """
    cache_key = 'mvrv_z_score'
    
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            logger.info(f"使用快取的 MVRV Z-Score: {cached['value']}")
            return cached['value']
    
    try:
        z_score = _fetch_glassnode_mvrv()
        if z_score is not None:
            _cache[cache_key] = {'value': z_score, 'timestamp': datetime.now()}
            return z_score
    except Exception as e:
        logger.warning(f"Glassnode API 失敗: {e}")
    
    try:
        z_score = _fetch_mvrv_from_public_chart()
        if z_score is not None:
            _cache[cache_key] = {'value': z_score, 'timestamp': datetime.now()}
            return z_score
    except Exception as e:
        logger.warning(f"圖表爬蟲失敗: {e}")
    
    logger.error("所有 MVRV 數據源失敗，使用降級估算")
    return _estimate_mvrv_from_price()


def _fetch_glassnode_mvrv() -> Optional[float]:
    """從 Glassnode API 獲取 MVRV Z-Score"""
    api_key = os.getenv('GLASSNODE_API_KEY')
    
    if not api_key:
        logger.warning("未設定 GLASSNODE_API_KEY，跳過")
        return None
    
    url = "https://api.glassnode.com/v1/metrics/indicators/mvrv_z_score"
    params = {'a': 'BTC', 'api_key': api_key, 'i': '24h'}
    
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    if data and len(data) > 0:
        latest = data[-1]['v']
        logger.info(f"Glassnode MVRV Z-Score: {latest:.2f}")
        return float(latest)
    
    return None


def _fetch_mvrv_from_public_chart() -> Optional[float]:
    """從公開圖表網站爬取 MVRV (備援方案)"""
    logger.warning("圖表爬蟲功能尚未實作")
    return None


def _estimate_mvrv_from_price() -> Optional[float]:
    """降級估算：使用價格相對 200週均線推估 MVRV"""
    try:
        ma_200w = get_200w_ma()
        if not ma_200w:
            return None
        
        exchange = get_exchange()
        ticker = exchange.fetch_ticker('BTC/USDT')
        current_price = ticker['last']
        
        multiplier = current_price / ma_200w
        
        if multiplier < 1.0:
            estimated_mvrv = 0.0
        elif multiplier < 1.5:
            estimated_mvrv = 1.0
        elif multiplier < 2.0:
            estimated_mvrv = 3.0
        elif multiplier < 3.0:
            estimated_mvrv = 5.0
        elif multiplier < 4.0:
            estimated_mvrv = 7.0
        else:
            estimated_mvrv = 9.0
        
        logger.warning(f"使用估算 MVRV: {estimated_mvrv:.1f} (價格倍數: {multiplier:.2f}x)")
        return estimated_mvrv
        
    except Exception as e:
        logger.error(f"降級估算失敗: {e}")
        return None


def get_200w_ma() -> Optional[float]:
    """計算 200週移動平均線"""
    cache_key = '200w_ma'
    
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            return cached['value']
    
    try:
        exchange = get_exchange()
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1w', limit=200)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        ma_200 = df['close'].mean()
        
        _cache[cache_key] = {'value': ma_200, 'timestamp': datetime.now()}
        logger.info(f"200週均線: ${ma_200:,.0f}")
        return float(ma_200)
        
    except Exception as e:
        logger.error(f"200週均線計算失敗: {e}")
        return None


def get_pi_cycle_top() -> Dict[str, Any]:
    """計算 Pi Cycle Top Indicator"""
    cache_key = 'pi_cycle'
    
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            return cached['value']
    
    try:
        exchange = get_exchange()
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1d', limit=400)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        dma_111 = df['close'].rolling(window=111).mean().iloc[-1]
        dma_350 = df['close'].rolling(window=350).mean().iloc[-1]
        dma_350_x2 = dma_350 * 2
        
        distance_pct = ((dma_111 - dma_350_x2) / dma_350_x2) * 100
        is_crossed = dma_111 > dma_350_x2
        
        if is_crossed:
            signal = 'SELL'
        elif distance_pct > -5:
            signal = 'CAUTION'
        else:
            signal = 'NORMAL'
        
        result = {
            '111dma': float(dma_111),
            '350dma_x2': float(dma_350_x2),
            'distance_pct': float(distance_pct),
            'is_crossed': is_crossed,
            'signal': signal
        }
        
        _cache[cache_key] = {'value': result, 'timestamp': datetime.now()}
        logger.info(f"Pi Cycle: 111DMA=${dma_111:,.0f}, 350DMA*2=${dma_350_x2:,.0f}, Signal={signal}")
        return result
        
    except Exception as e:
        logger.error(f"Pi Cycle 計算失敗: {e}")
        return {'111dma': 0, '350dma_x2': 0, 'distance_pct': 0, 'is_crossed': False, 'signal': 'ERROR'}


def get_monthly_rsi(period: int = 14) -> Optional[float]:
    """獲取月線級別 RSI"""
    cache_key = f'monthly_rsi_{period}'
    
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            return cached['value']
    
    try:
        import pandas_ta as ta
        
        exchange = get_exchange()
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1M', limit=100)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        rsi = ta.rsi(df['close'], length=period)
        current_rsi = rsi.iloc[-1]
        
        _cache[cache_key] = {'value': current_rsi, 'timestamp': datetime.now()}
        logger.info(f"月線 RSI: {current_rsi:.1f}")
        return float(current_rsi)
        
    except Exception as e:
        logger.error(f"月線 RSI 計算失敗: {e}")
        return None


def get_market_valuation_summary() -> Dict[str, Any]:
    """綜合市場估值摘要"""
    mvrv = get_mvrv_z_score()
    pi_cycle = get_pi_cycle_top()
    ma_200w = get_200w_ma()
    monthly_rsi = get_monthly_rsi()
    
    risk_score = 0
    
    if mvrv:
        if mvrv > 7:
            risk_score += 3
        elif mvrv > 6:
            risk_score += 2
        elif mvrv < 1:
            risk_score -= 2
        elif mvrv < 0.1:
            risk_score -= 3
    
    if pi_cycle['signal'] == 'SELL':
        risk_score += 3
    elif pi_cycle['signal'] == 'CAUTION':
        risk_score += 1
    
    if monthly_rsi:
        if monthly_rsi > 85:
            risk_score += 2
        elif monthly_rsi < 45:
            risk_score -= 2
    
    if risk_score >= 5:
        overall_risk = 'EXTREME'
        recommendation = '極度過熱，建議停止買入並執行賣出計畫'
    elif risk_score >= 3:
        overall_risk = 'HIGH'
        recommendation = '市場過熱，減少投入或暫停 DCA'
    elif risk_score >= -1:
        overall_risk = 'MEDIUM'
        recommendation = '正常區間，繼續標準 DCA'
    else:
        overall_risk = 'LOW'
        recommendation = '低估區域，建議加大投入倍數'
    
    return {
        'mvrv_z_score': mvrv,
        'pi_cycle': pi_cycle,
        '200w_ma': ma_200w,
        'monthly_rsi': monthly_rsi,
        'overall_risk': overall_risk,
        'recommendation': recommendation,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("MVRV 數據源測試")
    print("=" * 60)
    
    summary = get_market_valuation_summary()
    
    print(f"\n市場估值摘要")
    print(f"MVRV Z-Score: {summary['mvrv_z_score']:.2f}" if summary['mvrv_z_score'] else "MVRV: 無數據")
    print(f"200週均線: ${summary['200w_ma']:,.0f}" if summary['200w_ma'] else "200WMA: 無數據")
    print(f"月線 RSI: {summary['monthly_rsi']:.1f}" if summary['monthly_rsi'] else "月線RSI: 無數據")
    print(f"\nPi Cycle Top:")
    print(f"  111DMA: ${summary['pi_cycle']['111dma']:,.0f}")
    print(f"  350DMA*2: ${summary['pi_cycle']['350dma_x2']:,.0f}")
    print(f"  信號: {summary['pi_cycle']['signal']}")
    print(f"\n整體風險: {summary['overall_risk']}")
    print(f"建議: {summary['recommendation']}")
