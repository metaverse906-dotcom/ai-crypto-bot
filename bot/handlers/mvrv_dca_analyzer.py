"""
MVRV DCA ?†æ?æ¨¡ç?

?ä??ºæ–¼ MVRV Z-Score ?„å???DCA å»ºè­°
?‡ç¾??F&G æ¨¡å?ä¸¦å?ï¼Œå¯?é??ç½®?‡æ?
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
import pytz
import pandas as pd
from core.mvrv_data_source import get_market_valuation_summary, get_mvrv_z_score
from core.position_manager import PositionManager
from config.strategy_config import strategy_config

logger = logging.getLogger(__name__)


async def get_mvrv_buy_multiplier(mvrv: float, rsi: float = None, fg: float = None, monthly_rsi: float = None, pi_cycle_crossed: bool = False) -> Dict[str, Any]:
    """
    ?¹æ?? æ??†æ•¸æ±ºå?è²·å…¥?æ•¸ï¼ˆå„ª?–å??€ä½³é?ç½®ï?
    
    ? æ?ç³»çµ±ï¼šMVRV 65% + RSI 25% + F&G 10%
    ?æ¸¬ç¸¾æ?ï¼?952% vs HODL (2020-2024)
    
    å®‰å…¨æ©Ÿåˆ¶ï¼?
    - Pi Cycle Top äº¤å? ??å¼·åˆ¶?œæ­¢è²·å…¥
    - ?ˆç? RSI > 85 ???¦æ±ºè²·å…¥ï¼ˆæ¥µç«¯é??±ï?
    
    Args:
        mvrv: MVRV Z-Score ??
        rsi: RSI ?¼ï??¯é¸ï¼?
        fg: Fear & Greed ?†æ•¸ï¼ˆå¯?¸ï?
        monthly_rsi: ?ˆç? RSIï¼ˆå??¨æ??¶ï?
        pi_cycle_crossed: Pi Cycle Top ?¯å¦äº¤å?ï¼ˆå??¨æ??¶ï?
        
    Returns:
        dict: {
            'multiplier': float,
            'recommendation': str,
            'reason': str,
            'emoji': str,
            'score': float,
            'safety_override': bool  # ?¯å¦è¢«å??¨æ??¶è???
        }
    """
    # ?š¨ å®‰å…¨æ©Ÿåˆ¶ 1: Pi Cycle Top äº¤å? ??çµ•å?ä¸è²·
    if pi_cycle_crossed:
        return {
            'multiplier': 0.0,
            'recommendation': '??Pi Cycle ?‚éƒ¨ä¿¡è? - ?œæ­¢è²·å…¥',
            'reason': 'Pi Cycle Top äº¤å?ï¼Œæ­·?²ä?æ¨™è??±æ??‚éƒ¨ï¼Œæš«?œæ??‰è²·??,
            'emoji': '?”´?”´?”´',
            'score': 100,
            'safety_override': True
        }
    
    # ?š¨ å®‰å…¨æ©Ÿåˆ¶ 2: ?ˆç? RSI > 85 ??æ¥µç«¯?ç†±?¦æ±º
    if monthly_rsi and monthly_rsi > 85:
        return {
            'multiplier': 0.0,
            'recommendation': '???ˆç?æ¥µåº¦?ç†± - ?œæ­¢è²·å…¥',
            'reason': f'?ˆç? RSI {monthly_rsi:.1f} æ¥µåº¦?ç†±ï¼Œå³ä½¿ä¼°?¼ä?ä¼°ä??«å?è²·å…¥',
            'emoji': '?”´?”´',
            'score': 95,
            'safety_override': True
        }
    
    # 1. MVRV ? å??°å??¸ï?0-100ï¼?
    if mvrv < 0.1:
        mvrv_score = 0
    elif mvrv < 1.0:
        mvrv_score = 10
    elif mvrv < 3.0:
        mvrv_score = 30
    elif mvrv < 5.0:
        mvrv_score = 50
    elif mvrv < 6.0:
        mvrv_score = 65
    elif mvrv < 7.0:
        mvrv_score = 80
    elif mvrv < 9.0:
        mvrv_score = 90
    else:
        mvrv_score = 100
    
    # 2. RSI å·²ç???0-100
    rsi_score = rsi if rsi and not pd.isna(rsi) else 50
    
    # 3. F&G å·²ç???0-100
    fg_score = fg if fg and not pd.isna(fg) else 50
    
    # 4. ? æ?çµ„å?ï¼ˆå??¸è?ä½?= è¶Šè©²è²·ï?
    # ?ªå?å¾Œæ?ä½³æ??ï?MVRV 65% + RSI 25% + F&G 10%
    # ?æ¸¬ç¸¾æ?ï¼?0.63 BTC vs HODL 2.91 BTC (+952%)
    composite_score = (mvrv_score * 0.65) + (rsi_score * 0.25) + (fg_score * 0.10)
    
    # 5. ?¹æ?ç¶œå??†æ•¸æ±ºå??æ•¸
    if composite_score < 15:  # æ¥µåº¦ä½ä¼°
        return {
            'multiplier': 3.5,
            'recommendation': 'æ¥µåº¦ä½ä¼° - ?¨å?? ç¢¼',
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f} (MVRV {mvrv:.2f}, RSI {rsi_score:.0f}, F&G {fg_score:.0f}) - æ­·å²ç´šè²·é»?,
            'emoji': '?Ÿ¢?Ÿ¢?Ÿ¢?Ÿ¢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 25:
        return {
            'multiplier': 2.0,
            'recommendation': 'å¼·å?ä½ä¼° - å¤§å?? ç¢¼',
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f} - ???æ©Ÿæ?',
            'emoji': '?Ÿ¢?Ÿ¢?Ÿ¢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 35:
        return {
            'multiplier': 1.5,
            'recommendation': 'ä½ä¼°?€??- ? ç¢¼è²·å…¥',
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f} - ?ç?ç´¯ç?',
            'emoji': '?Ÿ¢?Ÿ¢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 50:
        return {
            'multiplier': 1.0,
            'recommendation': 'æ­?¸¸?€??- å®šæ?è²·å…¥',
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f} - ä¿æ?å®šæ?',
            'emoji': '?Ÿ¢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 60:
        return {
            'multiplier': 0.5,
            'recommendation': 'è¼•åº¦é«˜ä¼° - æ¸›é€Ÿè²·??,
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f} - è¬¹æ??•å…¥',
            'emoji': '?Ÿ¡',
            'score': composite_score,
            'safety_override': False
        }
    else:
        return {
            'multiplier': 0.0,
            'recommendation': '?ç†±?€??- ?œæ­¢è²·å…¥',
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f} - ?«å?å®šæ?',
            'emoji': '?”´',
            'score': composite_score,
            'safety_override': False
        }


async def get_mvrv_sell_recommendation(mvrv: float, rsi: float, fg: float, position_manager: PositionManager, current_price: float, pi_cycle_crossed: bool = False) -> Dict[str, Any]:
    """
    ?¹æ?? æ??†æ•¸æ±ºå??¯å¦è³?‡ºï¼ˆåª?å?äº¤æ??‰ï?
    
    å®‰å…¨æ©Ÿåˆ¶ï¼šPi Cycle Top äº¤å? ??ç«‹å³æ¸…ç©ºäº¤æ???
    
    Args:
        mvrv: MVRV Z-Score ??
        rsi: RSI ??
        fg: Fear & Greed ?†æ•¸
        position_manager: ?‰ä?ç®¡ç???
        current_price: ?¶å??¹æ ¼
        pi_cycle_crossed: Pi Cycle Top ?¯å¦äº¤å?
        
    Returns:
        dict: è³?‡ºå»ºè­°
    """
    stats = position_manager.get_stats()
    trade_btc = stats['trade_btc']
    
    # ?š¨ å®‰å…¨æ©Ÿåˆ¶: Pi Cycle Top äº¤å? ??å¼·åˆ¶è³?‡º?€?‰äº¤?“å€?
    if pi_cycle_crossed:
        return {
            'should_sell': True,
            'sell_pct': 1.0,
            'sell_btc': trade_btc,
            'reason': '?š¨ Pi Cycle Top äº¤å?ï¼æ­·?²é??¨ä¿¡?Ÿï?ç«‹å³æ¸…ç©ºäº¤æ???,
            'safety_override': True
        }
    
    # è¨ˆç?ç¶œå??†æ•¸
    if mvrv < 0.1:
        mvrv_score = 0
    elif mvrv < 1.0:
        mvrv_score = 10
    elif mvrv < 3.0:
        mvrv_score = 30
    elif mvrv < 5.0:
        mvrv_score = 50
    elif mvrv < 6.0:
        mvrv_score = 65
    elif mvrv < 7.0:
        mvrv_score = 80
    elif mvrv < 9.0:
        mvrv_score = 90
    else:
        mvrv_score = 100
    
    rsi_score = rsi if not pd.isna(rsi) else 50
    fg_score = fg if not pd.isna(fg) else 50
    
    composite_score = (mvrv_score * 0.65) + (rsi_score * 0.25) + (fg_score * 0.10)
    
    # ?¹æ??†æ•¸æ±ºå?è³?‡º
    if composite_score < 70:
        return {
            'should_sell': False,
            'sell_pct': 0.0,
            'sell_btc': 0.0,
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f}ï¼Œå??ªé???,
            'safety_override': False
        }
    elif composite_score < 80:
        sell_pct = 0.10
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f}ï¼Œè?åº¦é??±ï?å»ºè­°è³?‡ºäº¤æ???{sell_pct*100:.0f}%',
            'safety_override': False
        }
    elif composite_score < 90:
        sell_pct = 0.30
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f}ï¼Œæ?é¡¯é??±ï?å»ºè­°å¤§å?æ¸›å€?,
            'safety_override': False
        }
    elif composite_score < 95:
        sell_pct = 0.50
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f}ï¼Œæ¥µåº¦é??±ï?å»ºè­°æ¸…å€‰ä???,
            'safety_override': False
        }
    else:
        sell_pct = 1.0
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'ç¶œå??†æ•¸ {composite_score:.0f}ï¼Œæ³¡æ²«å??Ÿï?å»ºè­°æ¸…ç©ºäº¤æ???,
            'safety_override': False
        }


async def get_mvrv_dca_analysis(current_price: float, position_manager: PositionManager = None) -> str:
    """
    ?²å? MVRV æ¨¡å???DCA ?†æ?ï¼ˆå?æ¬Šå??¸ç??¥ï?
    
    Args:
        current_price: ?¶å? BTC ?¹æ ¼
        position_manager: ?‰ä?ç®¡ç??¨ï??¯é¸ï¼?
        
    Returns:
        str: ?¼å??–ç??†æ?è¨Šæ¯
    """
    try:
        # 1. ?²å? MVRV ç¶œå??˜è?
        summary = await asyncio.to_thread(get_market_valuation_summary)
        
        mvrv = summary['mvrv_z_score']
        pi_cycle = summary['pi_cycle']
        ma_200w = summary['200w_ma']
        monthly_rsi = summary['monthly_rsi']
        overall_risk = summary['overall_risk']
        
        # 2. ?²å? RSI ??F&Gï¼ˆç”¨?¼å?æ¬Šï?
        import ccxt
        exchange = get_exchange()
        
        # ?²å??¥ç? RSI
        ohlcv = await asyncio.to_thread(
            exchange.fetch_ohlcv,
            'BTC/USDT',
            '1d',
            limit=100
        )
        import pandas_ta as ta
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        daily_rsi = ta.rsi(df['close'], length=14).iloc[-1]
        
        # ?²å? F&G
        import requests
        try:
            response = await asyncio.to_thread(
                requests.get,
                'https://api.alternative.me/fng/',
                timeout=5
            )
            fg_data = response.json()
            fg_score = int(fg_data['data'][0]['value'])
        except:
            fg_score = 50  # ?ç?
        
        # 3. æ±ºå?è²·å…¥?æ•¸ï¼ˆä½¿?¨å?æ¬Šå???+ å®‰å…¨æ©Ÿåˆ¶ï¼?
        buy_decision = await get_mvrv_buy_multiplier(
            mvrv if mvrv else 1.0,
            daily_rsi,
            fg_score,
            monthly_rsi,  # ?ˆç? RSI å®‰å…¨æ©Ÿåˆ¶
            pi_cycle.get('is_crossed', False)  # Pi Cycle å®‰å…¨æ©Ÿåˆ¶
        )
        
        # 4. è¨ˆç?è²·å…¥?‘é?
        base_weekly = strategy_config.BASE_WEEKLY_USD
        buy_amount_usd = base_weekly * buy_decision['multiplier']
        
        # 5. æª¢æŸ¥?¯å¦?€è¦è³£??
        sell_info = None
        if position_manager and mvrv:
            sell_info = await get_mvrv_sell_recommendation(
                mvrv, daily_rsi, fg_score, position_manager, current_price,
                pi_cycle.get('is_crossed', False)  # Pi Cycle å¼·åˆ¶è³?‡º
            )
        
        # 5. è¨ˆç?ä¸‹æ¬¡?ªå??¨é€æ???
        taipei_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(taipei_tz)
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 20:
            days_until_sunday = 7
        next_push = now + timedelta(days=days_until_sunday)
        next_push = next_push.replace(hour=20, minute=0, second=0, microsecond=0)
        next_push_str = next_push.strftime('%m/%dï¼?aï¼‰æ?ä¸?8:00')
        
        # 6. çµ„å?è¨Šæ¯
        # æª¢æŸ¥?¯å¦?‰å??¨æ??¶è§¸??
        safety_alert = ""
        if buy_decision.get('safety_override'):
            safety_alert = "\n\n?š¨ **å®‰å…¨æ©Ÿåˆ¶å·²è§¸??* ?š¨\n"
        
        message = f"""
?? **Smart DCA ?¬é€±å»ºè­°ï?? æ??†æ•¸ç­–ç•¥ï¼?*

{buy_decision['emoji']} **{buy_decision['recommendation']}**
{safety_alert}
**å¸‚å ´ä¼°å€¼ç???*
BTC ?¹æ ¼ï¼?{current_price:,.0f}
ç¶œå??†æ•¸ï¼š{buy_decision['score']:.0f}/100 â­?

**?ˆä??‡æ?ï¼ˆMVRV 65%æ¬Šé?ï¼?*
MVRV Z-Scoreï¼š{mvrv:.2f if mvrv else 'N/A'}
200?±å?ç·šï?${ma_200w:,.0f if ma_200w else 'N/A'}

**?€è¡“æ?æ¨™ï?RSI 25%æ¬Šé?ï¼?*
?¥ç? RSIï¼š{daily_rsi:.1f if daily_rsi else 'N/A'}
?ˆç? RSIï¼š{monthly_rsi:.1f if monthly_rsi else 'N/A'}{' ? ï? æ¥µåº¦?ç†±' if monthly_rsi and monthly_rsi > 85 else ''}

**?…ç??‡æ?ï¼ˆF&G 10%æ¬Šé?ï¼?*
Fear & Greedï¼š{fg_score}

**Pi Cycle Top**
111DMAï¼?{pi_cycle['111dma']:,.0f}
350DMA?2ï¼?{pi_cycle['350dma_x2']:,.0f}
ä¿¡è?ï¼š{pi_cycle['signal']}{' ?š¨ ?‚éƒ¨è­¦å?ï¼? if pi_cycle.get('is_crossed') else ''}

**?†æ?**
{buy_decision['reason']}

**?¬é€±è²·?¥å»ºè­?*
${buy_amount_usd:.0f} ({buy_decision['multiplier']}x ?æ•¸)
"""
        
        # 7. å¦‚æ??‰è³£?ºå»ºè­?
        if sell_info and sell_info['should_sell']:
            sell_alert_icon = "?š¨?š¨?š¨" if sell_info.get('safety_override') else "? ï?"
            message += f"""
{sell_alert_icon} **è³?‡ºå»ºè­°**
{sell_info['reason']}
å»ºè­°è³?‡ºï¼š{sell_info['sell_btc']:.6f} BTCï¼ˆäº¤?“å€?{sell_info['sell_pct']*100:.0f}%ï¼?
"""
        
        # 8. ?å€‰ä¿¡?¯ï?å¦‚æ??‰ï?
        if position_manager:
            stats = position_manager.get_stats()
            pnl = position_manager.get_unrealized_pnl(current_price)
            
            message += f"""
?? **?å€‰ç?æ³?*
ç¸½æ??‰ï?{stats['total_btc']:.6f} BTC
?œâ? ?¸å??‰ï?{stats['core_btc']:.6f} BTCï¼ˆæ???${stats['core_avg_cost']:,.0f}ï¼?
?”â? äº¤æ??‰ï?{stats['trade_btc']:.6f} BTCï¼ˆæ???${stats['trade_avg_cost']:,.0f}ï¼?

å¹³å??æœ¬ï¼?{stats['avg_cost']:,.0f}
?ªå¯¦?¾ç??§ï?${pnl['unrealized_pnl']:,.0f} ({pnl['roi_pct']:+.1f}%)
"""
        
        # 9. ?·è?ç­–ç•¥èªªæ?
        message += f"""
**?·è?ç­–ç•¥**
???¸å??‰ï?{strategy_config.MVRV_CORE_RATIO*100:.0f}% ?“æ­»ä¸è³£
??äº¤æ??‰ï?{(1-strategy_config.MVRV_CORE_RATIO)*100:.0f}% ?¹æ??±æ?è³?‡º
???‚é?ï¼šå??¹åŸ·è¡Œï??¿å??®é?é¢¨éšª

**?ªå??’ç?**
?? ä¸‹æ¬¡?¨é€ï?{next_push_str}
?? ?ºå??‚é?ï¼šæ??±æ—¥?šä? 8:00ï¼ˆå°?—æ??“ï?

?? ?¸æ?æºï?MVRV Z-Score + Pi Cycle + 200WMA
"""
        
        return message.strip()
        
    except Exception as e:
        logger.error(f"MVRV DCA ?†æ?å¤±æ?: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    # æ¸¬è©¦
    import ccxt
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        exchange = get_exchange()
        ticker = exchange.fetch_ticker('BTC/USDT')
        price = ticker['last']
        
        message = await get_mvrv_dca_analysis(price)
        print(message)
    
    asyncio.run(test())
