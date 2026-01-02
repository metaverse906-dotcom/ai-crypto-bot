#!/usr/bin/env python3
"""
MVRV це╡члпцйЯц??╡ц╕м??

цпПхдй 3 цмбя??????Ъя?цквцЯея╝?
- MVRV це╡х║жф╜Оф╝░я╝? 0.5я╝?
- ч╢Ьх??ЖцХ╕ < 20
- Pi Cycle ф║дх?

?╝чП╛це╡члпцйЯц?члЛхН│ Telegram шнжха▒
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import asyncio
import logging
from datetime import datetime
from core.mvrv_data_source import get_market_valuation_summary
from core.signal_notifier import SignalNotifier
import ccxt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MVRVPanicDetector:
    """MVRV це╡члпцйЯц??╡ц╕м??""
    
    def __init__(self):
        self.notifier = SignalNotifier()
        
        # це╡члп?╛хА╝я?цпФцнгх╕╕цЫ┤ц┐А?▓я?
        self.EXTREME_MVRV = 0.5  # MVRV < 0.5 = це╡х║жф╜Оф╝░
        self.EXTREME_SCORE = 20   # ч╢Ьх??ЖцХ╕ < 20 = це╡члпцйЯц?
    
    async def check_extreme_opportunity(self):
        """цквцЯе?пхРж?Йце╡члпш▓╖?ец???""
        try:
            logger.info("?? ?Лх?цквц╕мце╡члпцйЯц?...")
            
            # 1. ?▓х?х╕Вха┤?╕ц?
            summary = get_market_valuation_summary()
            
            mvrv = summary.get('mvrv_z_score')
            pi_cycle = summary.get('pi_cycle', {})
            
            # 2. ?▓х??╢х??╣ца╝??RSI
            exchange = get_exchange()
            ticker = await asyncio.to_thread(exchange.fetch_ticker, 'BTC/USDT')
            current_price = ticker['last']
            
            # ?▓х? RSI
            ohlcv = await asyncio.to_thread(
                exchange.fetch_ohlcv,
                'BTC/USDT',
                '1d',
                limit=100
            )
            import pandas as pd
            import pandas_ta as ta
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            rsi = ta.rsi(df['close'], length=14).iloc[-1]
            
            # ?▓х? F&G
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
                fg_score = 50
            
            # 3. шиИч?ч╢Ьх??ЖцХ╕
            if mvrv < 0.1:
                mvrv_score = 0
            elif mvrv < 1.0:
                mvrv_score = 10
            elif mvrv < 3.0:
                mvrv_score = 30
            else:
                mvrv_score = 50
            
            composite_score = (mvrv_score * 0.65) + (rsi * 0.25) + (fg_score * 0.10)
            
            # 4. цквцЯеце╡члпцвЭф╗╢
            alerts = []
            
            # це╡члпф╜Оф╝░
            if mvrv and mvrv < self.EXTREME_MVRV:
                alerts.append(f"?Ъи MVRV це╡х║жф╜Оф╝░я╝Ъ{mvrv:.2f}")
            
            # ч╢Ьх??ЖцХ╕це╡ф?
            if composite_score < self.EXTREME_SCORE:
                alerts.append(f"?Ъи ч╢Ьх??ЖцХ╕це╡ф?я╝Ъ{composite_score:.0f}")
            
            # Pi Cycle ?ВщГиф║дх?я╝Их??Сшнж?Кя?
            if pi_cycle.get('is_crossed'):
                alerts.append(f"??Pi Cycle ?ВщГиф║дх?я╝Бч??│х?цнвш▓╖?ея?")
            
            # 5. ?╝щАБшнж??
            if alerts:
                await self._send_alert(alerts, current_price, mvrv, composite_score, rsi, fg_score)
            else:
                logger.info("???бце╡члпц??Гя?х╕Вха┤цн?╕╕")
            
        except Exception as e:
            logger.error(f"??цквц╕мхд▒ц?: {e}", exc_info=True)
    
    async def _send_alert(self, alerts, price, mvrv, score, rsi, fg):
        """?╝щАБце╡члпц??Гшнж??""
        
        alert_msg = "\n".join([f"  ??{a}" for a in alerts])
        
        # ?дцЦ╖?пш▓╖?ещ??пш│г?║шнж??
        if "Pi Cycle" in alert_msg:
            emoji = "??
            title = "це╡члпш│?З║шнжха▒"
            suggestion = "члЛхН│ц╕Ечй║ф║дц??Йя?"
        else:
            emoji = "?Ъи"
            title = "це╡члпш▓╖хЕецйЯц?"
            suggestion = "?ГцЕохдзх??ачв╝я╝?
        
        message = f"""
{emoji} **{title}** {emoji}

{alert_msg}

**?╢х?х╕Вха┤**
BTC ?╣ца╝я╝?{price:,.0f}
MVRV Z-Scoreя╝Ъ{mvrv:.2f if mvrv else 'N/A'}
ч╢Ьх??ЖцХ╕я╝Ъ{score:.0f}/100
RSIя╝Ъ{rsi:.1f}
F&Gя╝Ъ{fg}

**х╗║шн░**
{suggestion}

??цквц╕м?Вщ?я╝Ъ{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
?Тб ?ЩцШп?кх?це╡члпцйЯц??╡ц╕мя╝Мц?хд?цм?

члЛхН│?╖ш? /dca_now ?еч?хоМцХ┤?Жц?
"""
        
        await self.notifier.send_notification(message, level='CRITICAL')
        logger.info(f"?Ъи х╖▓чЩ╝?Бце╡члпшнж?▒я?{len(alerts)} ?Лшз╕?╝ц?ф╗?)


async def main():
    """ф╕╗ч?х║?""
    detector = MVRVPanicDetector()
    await detector.check_extreme_opportunity()


if __name__ == '__main__':
    asyncio.run(main())
