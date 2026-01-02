"""
MVRV Z-Score ?¸æ?æºæ¨¡çµ?

?ä?æ¯”ç‰¹å¹??ä¸Šä¼°?¼æ?æ¨™ï?
- MVRV Z-Score (å¸‚å€?å·²å¯¦?¾åƒ¹??Z ?†æ•¸)
- Pi Cycle Top Indicator (111DMA vs 350DMA?2)
- 200?±ç§»?•å¹³?‡ç?

?¸æ?ä¾†æ?ç­–ç•¥ï¼?
1. Glassnode API (?è²»å±¤ï??ªå?)
2. ?ç??°è?ç®—è?ä¼¼å€¼ï?ä½¿ç”¨?¹æ ¼?¸æ?ï¼?
3. å¿«å?æ©Ÿåˆ¶æ¸›å? API èª¿ç”¨
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

# å¿«å?è¨­å?
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_DURATION = timedelta(hours=24)  # æ¯æ—¥?´æ–°ä¸€æ¬¡å³??

class MVRVDataError(Exception):
    """MVRV ?¸æ??²å??¯èª¤"""
    pass


def get_mvrv_z_score() -> Optional[float]:
    """
    ?²å? MVRV Z-Score
    
    MVRV Z-Score = (Market Cap - Realized Cap) / std(Market Cap)
    
    Returns:
        float: Z-Score ?¼ï?ç¯„å??šå¸¸??-1 ??10
        None: ?²å?å¤±æ?
        
    ?¾å€¼å??ƒï?
        < 0.1: æ¥µåº¦ä½ä¼°ï¼ˆæ­·?²å??¨ï?
        1.0-5.0: æ­?¸¸?€??
        > 6.0: ?‹å??ç†±
        > 7.0: æ¥µåº¦?ç†±ï¼ˆæ­·?²é??¨ï?
    """
    cache_key = 'mvrv_z_score'
    
    # æª¢æŸ¥å¿«å?
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            logger.info(f"ä½¿ç”¨å¿«å???MVRV Z-Score: {cached['value']}")
            return cached['value']
    
    try:
        # ?¹æ? 1: Glassnode ?è²» API
        z_score = _fetch_glassnode_mvrv()
        if z_score is not None:
            _cache[cache_key] = {'value': z_score, 'timestamp': datetime.now()}
            return z_score
            
    except Exception as e:
        logger.warning(f"Glassnode API å¤±æ?: {e}")
    
    try:
        # ?¹æ? 2: ?ç? - ä½¿ç”¨?¬é??–è¡¨?¬èŸ²ï¼ˆå??´ï?
        z_score = _fetch_mvrv_from_public_chart()
        if z_score is not None:
            _cache[cache_key] = {'value': z_score, 'timestamp': datetime.now()}
            return z_score
            
    except Exception as e:
        logger.warning(f"?–è¡¨?¬èŸ²å¤±æ?: {e}")
    
    # ?¹æ? 3: æ¥µç«¯?ç? - ä½¿ç”¨?¹æ ¼?¸å? 200WMA ä½œç‚ºç²—ç•¥ä¼°ç?
    logger.error("?€??MVRV ?¸æ?æºå¤±?—ï?ä½¿ç”¨?ç?ä¼°ç?")
    return _estimate_mvrv_from_price()


def _fetch_glassnode_mvrv() -> Optional[float]:
    """
    å¾?Glassnode API ?²å? MVRV Z-Score
    
    ?€è¦ç’°å¢ƒè??¸ï?GLASSNODE_API_KEY
    ?è²»å±¤é??¶ï?æ¯å???60 æ¬¡è?æ±?
    """
    api_key = os.getenv('GLASSNODE_API_KEY')
    
    if not api_key:
        logger.warning("?ªè¨­å®?GLASSNODE_API_KEYï¼Œè·³??)
        return None
    
    url = "https://api.glassnode.com/v1/metrics/indicators/mvrv_z_score"
    params = {
        'a': 'BTC',  # è³‡ç”¢
        'api_key': api_key,
        'i': '24h'   # ?¥ç?ç´šåˆ¥
    }
    
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    if data and len(data) > 0:
        # ?–æ??°å€?
        latest = data[-1]['v']
        logger.info(f"??Glassnode MVRV Z-Score: {latest:.2f}")
        return float(latest)
    
    return None


def _fetch_mvrv_from_public_chart() -> Optional[float]:
    """
    å¾å…¬?‹å?è¡¨ç¶²ç«™çˆ¬??MVRV (?™æ´?¹æ?)
    
    æ³¨æ?ï¼šæ­¤?¹æ?ä¾è³´ç¶²é?çµæ?ï¼Œå¯?½ä?ç©©å?
    """
    # ?¯é¸?¹æ?ï¼?
    # 1. lookintobitcoin.com ??MVRV chart
    # 2. bitcoinmagazinepro.com charts
    
    # ?™è£¡?ˆè???Noneï¼Œå??‰é?è¦å¯å¯¦ä??¬èŸ²
    logger.warning("?–è¡¨?¬èŸ²?Ÿèƒ½å°šæœªå¯¦ä?")
    return None


def _estimate_mvrv_from_price() -> Optional[float]:
    """
    ?ç?ä¼°ç?ï¼šä½¿?¨åƒ¹?¼ç›¸å°?200?±å?ç·šæ¨ä¼?MVRV
    
    ?™ä??¯ç?æ­?? MVRVï¼Œä??¯ä»¥ä½œç‚ºæ¥µç«¯?ç??¹æ?
    
    ç²—ç•¥? å??œä?ï¼?
    - Price near 200WMA ??MVRV ??1.0
    - Price = 2x 200WMA ??MVRV ??3.0  
    - Price = 3x 200WMA ??MVRV ??6.0
    - Price = 4x+ 200WMA ??MVRV ??8.0+
    """
    try:
        ma_200w = get_200w_ma()
        if not ma_200w:
            return None
            
        # ?²å??¶å??¹æ ¼
        exchange = get_exchange()
        ticker = exchange.fetch_ticker('BTC/USDT')
        current_price = ticker['last']
        
        # è¨ˆç??¹æ ¼?æ•¸
        multiplier = current_price / ma_200w
        
        # ç²—ç•¥? å???MVRV ç¯„å?
        if multiplier < 1.0:
            estimated_mvrv = 0.0  # æ¥µåº¦ä½ä¼°
        elif multiplier < 1.5:
            estimated_mvrv = 1.0
        elif multiplier < 2.0:
            estimated_mvrv = 3.0
        elif multiplier < 3.0:
            estimated_mvrv = 5.0
        elif multiplier < 4.0:
            estimated_mvrv = 7.0
        else:
            estimated_mvrv = 9.0  # æ¥µåº¦?ç†±
            
        logger.warning(f"? ï? ä½¿ç”¨ä¼°ç? MVRV: {estimated_mvrv:.1f} (?¹æ ¼?æ•¸: {multiplier:.2f}x)")
        return estimated_mvrv
        
    except Exception as e:
        logger.error(f"?ç?ä¼°ç?å¤±æ?: {e}")
        return None


def get_200w_ma() -> Optional[float]:
    """
    è¨ˆç? 200?±ç§»?•å¹³?‡ç?
    
    ?™æ˜¯æ¯”ç‰¹å¹???Œç??½ç??ï?æ­·å²ä¸Šåƒ¹?¼æ¥µå°‘é•·?Ÿä??¼æ­¤ç·?
    
    Returns:
        float: 200?±å???
        None: è¨ˆç?å¤±æ?
    """
    cache_key = '200w_ma'
    
    # æª¢æŸ¥å¿«å?
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            return cached['value']
    
    try:
        exchange = get_exchange()
        
        # 200??= 1400å¤?
        ohlcv = exchange.fetch_ohlcv(
            'BTC/USDT',
            timeframe='1w',
            limit=200
        )
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        ma_200 = df['close'].mean()
        
        _cache[cache_key] = {'value': ma_200, 'timestamp': datetime.now()}
        logger.info(f"200?±å?ç·? ${ma_200:,.0f}")
        return float(ma_200)
        
    except Exception as e:
        logger.error(f"200?±å?ç·šè?ç®—å¤±?? {e}")
        return None


def get_pi_cycle_top() -> Dict[str, Any]:
    """
    è¨ˆç? Pi Cycle Top Indicator
    
    ä¿¡è?ï¼?11DMA ?‘ä?ç©¿è? 350DMA?2 ?‚ï?æ­·å²ä¸Šç²¾ç¢ºæ?è¨˜é€±æ??‚éƒ¨
    
    Returns:
        dict: {
            '111dma': float,
            '350dma_x2': float,
            'distance_pct': float,  # ?©ç?è·é›¢?¾å?æ¯?
            'is_crossed': bool,     # ?¯å¦å·²äº¤??
            'signal': str          # 'SELL' / 'CAUTION' / 'NORMAL'
        }
    """
    cache_key = 'pi_cycle'
    
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            return cached['value']
    
    try:
        exchange = get_exchange()
        
        # ?€è¦?350 å¤©ç??¥ç??¸æ?
        ohlcv = exchange.fetch_ohlcv(
            'BTC/USDT',
            timeframe='1d',
            limit=400
        )
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # è¨ˆç??©æ??‡ç?
        dma_111 = df['close'].rolling(window=111).mean().iloc[-1]
        dma_350 = df['close'].rolling(window=350).mean().iloc[-1]
        dma_350_x2 = dma_350 * 2
        
        # è¨ˆç?è·é›¢
        distance_pct = ((dma_111 - dma_350_x2) / dma_350_x2) * 100
        is_crossed = dma_111 > dma_350_x2
        
        # ?¤æ–·ä¿¡è?
        if is_crossed:
            signal = 'SELL'
        elif distance_pct > -5:  # ?¥è?äº¤å?ï¼?%ä»¥å…§ï¼?
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
        logger.info(f"Pi Cycle: 111DMA=${dma_111:,.0f}, 350DMA?2=${dma_350_x2:,.0f}, Signal={signal}")
        return result
        
    except Exception as e:
        logger.error(f"Pi Cycle è¨ˆç?å¤±æ?: {e}")
        return {
            '111dma': 0,
            '350dma_x2': 0,
            'distance_pct': 0,
            'is_crossed': False,
            'signal': 'ERROR'
        }


def get_monthly_rsi(period: int = 14) -> Optional[float]:
    """
    ?²å??ˆç?ç´šåˆ¥ RSI
    
    ?ˆç? RSI ?¨çŸ­?±æ?ä¸Šå?æ»¿é?è¨Šï?ä½†åœ¨?ˆç?ç´šåˆ¥æ¥µå…·?‡å??ç¾©
    æ­·å²è¦å?ï¼šæ??‹ä¸»è¦é€±æ??‚éƒ¨ï¼Œæ?ç·?RSI ?½è???90
    
    Args:
        period: RSI ?±æ?ï¼Œé?è¨?14
        
    Returns:
        float: ?ˆç? RSI ??
        None: è¨ˆç?å¤±æ?
    """
    cache_key = f'monthly_rsi_{period}'
    
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            return cached['value']
    
    try:
        import pandas_ta as ta
        
        exchange = get_exchange()
        
        # ?²å??ˆç??¸æ?ï¼ˆé?è¦è¶³å¤ ç?æ­·å²ï¼?
        ohlcv = exchange.fetch_ohlcv(
            'BTC/USDT',
            timeframe='1M',
            limit=100
        )
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # ä½¿ç”¨ pandas_ta è¨ˆç? RSI
        rsi = ta.rsi(df['close'], length=period)
        current_rsi = rsi.iloc[-1]
        
        _cache[cache_key] = {'value': current_rsi, 'timestamp': datetime.now()}
        logger.info(f"?ˆç? RSI: {current_rsi:.1f}")
        return float(current_rsi)
        
    except Exception as e:
        logger.error(f"?ˆç? RSI è¨ˆç?å¤±æ?: {e}")
        return None


def get_market_valuation_summary() -> Dict[str, Any]:
    """
    ç¶œå?å¸‚å ´ä¼°å€¼æ?è¦?
    
    ?´å??€?‰é?ä¸Šæ?æ¨™ï??ä??®ä??„å??´ç??‹è?ä¼?
    
    Returns:
        dict: {
            'mvrv_z_score': float,
            'pi_cycle': dict,
            '200w_ma': float,
            'monthly_rsi': float,
            'overall_risk': str,  # 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
            'recommendation': str
        }
    """
    mvrv = get_mvrv_z_score()
    pi_cycle = get_pi_cycle_top()
    ma_200w = get_200w_ma()
    monthly_rsi = get_monthly_rsi()
    
    # ç¶œå?é¢¨éšªè©•ä¼°
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
    
    # ? å??°é¢¨?ªç?ç´?
    if risk_score >= 5:
        overall_risk = 'EXTREME'
        recommendation = '?”´ æ¥µåº¦?ç†±ï¼Œå»ºè­°å?æ­¢è²·?¥ä¸¦?·è?è³?‡ºè¨ˆç•«'
    elif risk_score >= 3:
        overall_risk = 'HIGH'
        recommendation = '?? å¸‚å ´?ç†±ï¼Œæ?å°‘æ??¥æ??«å? DCA'
    elif risk_score >= -1:
        overall_risk = 'MEDIUM'
        recommendation = '?Ÿ¡ æ­?¸¸?€?“ï?ç¹¼ç?æ¨™æ? DCA'
    else:
        overall_risk = 'LOW'
        recommendation = '?Ÿ¢ ä½ä¼°?€?Ÿï?å»ºè­°? å¤§?•å…¥?æ•¸'
    
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
    # æ¸¬è©¦?¨é€?
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("MVRV ?¸æ?æºæ¸¬è©?)
    print("=" * 60)
    
    summary = get_market_valuation_summary()
    
    print(f"\n?? å¸‚å ´ä¼°å€¼æ?è¦?)
    print(f"MVRV Z-Score: {summary['mvrv_z_score']:.2f}" if summary['mvrv_z_score'] else "MVRV: ?¡æ•¸??)
    print(f"200?±å?ç·? ${summary['200w_ma']:,.0f}" if summary['200w_ma'] else "200WMA: ?¡æ•¸??)
    print(f"?ˆç? RSI: {summary['monthly_rsi']:.1f}" if summary['monthly_rsi'] else "?ˆç?RSI: ?¡æ•¸??)
    print(f"\nPi Cycle Top:")
    print(f"  111DMA: ${summary['pi_cycle']['111dma']:,.0f}")
    print(f"  350DMA?2: ${summary['pi_cycle']['350dma_x2']:,.0f}")
    print(f"  ä¿¡è?: {summary['pi_cycle']['signal']}")
    print(f"\n?´é?é¢¨éšª: {summary['overall_risk']}")
    print(f"å»ºè­°: {summary['recommendation']}")
