#!/usr/bin/env python3
"""
MVRV 極端機會偵測器

每天 3 次（早/午/晚）檢查：
- MVRV 極度低估（< 0.5）
- 綜合分數 < 20
- Pi Cycle 交叉

發現極端機會立即 Telegram 警報
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
    """MVRV 極端機會偵測器"""
    
    def __init__(self):
        self.notifier = SignalNotifier()
        
        # 極端閾值（比正常更激進）
        self.EXTREME_MVRV = 0.5  # MVRV < 0.5 = 極度低估
        self.EXTREME_SCORE = 20   # 綜合分數 < 20 = 極端機會
    
    async def check_extreme_opportunity(self):
        """檢查是否有極端買入機會"""
        try:
            logger.info("🔍 開始檢測極端機會...")
            
            # 1. 獲取市場數據
            summary = get_market_valuation_summary()
            
            mvrv = summary.get('mvrv_z_score')
            pi_cycle = summary.get('pi_cycle', {})
            
            # 2. 獲取當前價格和 RSI
            exchange = ccxt.binance()
            ticker = await asyncio.to_thread(exchange.fetch_ticker, 'BTC/USDT')
            current_price = ticker['last']
            
            # 獲取 RSI
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
            
            # 獲取 F&G
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
            
            # 3. 計算綜合分數
            if mvrv < 0.1:
                mvrv_score = 0
            elif mvrv < 1.0:
                mvrv_score = 10
            elif mvrv < 3.0:
                mvrv_score = 30
            else:
                mvrv_score = 50
            
            composite_score = (mvrv_score * 0.65) + (rsi * 0.25) + (fg_score * 0.10)
            
            # 4. 檢查極端條件
            alerts = []
            
            # 極端低估
            if mvrv and mvrv < self.EXTREME_MVRV:
                alerts.append(f"🚨 MVRV 極度低估：{mvrv:.2f}")
            
            # 綜合分數極低
            if composite_score < self.EXTREME_SCORE:
                alerts.append(f"🚨 綜合分數極低：{composite_score:.0f}")
            
            # Pi Cycle 頂部交叉（反向警告）
            if pi_cycle.get('is_crossed'):
                alerts.append(f"⛔ Pi Cycle 頂部交叉！立即停止買入！")
            
            # 5. 發送警報
            if alerts:
                await self._send_alert(alerts, current_price, mvrv, composite_score, rsi, fg_score)
            else:
                logger.info("✅ 無極端機會，市場正常")
            
        except Exception as e:
            logger.error(f"❌ 檢測失敗: {e}", exc_info=True)
    
    async def _send_alert(self, alerts, price, mvrv, score, rsi, fg):
        """發送極端機會警報"""
        
        alert_msg = "\n".join([f"  • {a}" for a in alerts])
        
        # 判斷是買入還是賣出警報
        if "Pi Cycle" in alert_msg:
            emoji = "⛔"
            title = "極端賣出警報"
            suggestion = "立即清空交易倉！"
        else:
            emoji = "🚨"
            title = "極端買入機會"
            suggestion = "考慮大力加碼！"
        
        message = f"""
{emoji} **{title}** {emoji}

{alert_msg}

**當前市場**
BTC 價格：${price:,.0f}
MVRV Z-Score：{mvrv:.2f if mvrv else 'N/A'}
綜合分數：{score:.0f}/100
RSI：{rsi:.1f}
F&G：{fg}

**建議**
{suggestion}

⏰ 檢測時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💡 這是自動極端機會偵測，每天3次

立即執行 /dca_now 查看完整分析
"""
        
        await self.notifier.send_notification(message, level='CRITICAL')
        logger.info(f"🚨 已發送極端警報：{len(alerts)} 個觸發條件")


async def main():
    """主程序"""
    detector = MVRVPanicDetector()
    await detector.check_extreme_opportunity()


if __name__ == '__main__':
    asyncio.run(main())
