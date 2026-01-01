#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fear & Greed Panic Detector
Runs 3x daily to detect extreme panic (F&G < 10)
Sends Telegram alert when opportunity detected
"""
import os
import sys
import logging
from datetime import datetime
import ccxt
import requests
from telegram import Bot
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

class PanicDetector:
    """Detect extreme panic opportunities"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
        self.exchange = ccxt.okx()
    
    def get_fear_greed(self):
        """
        Get Fear & Greed index from API
        Returns: (score, classification)
        """
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            data = response.json()
            score = int(data['data'][0]['value'])
            classification = data['data'][0]['value_classification']
            return score, classification
        except Exception as e:
            logger.error(f"Failed to get F&G: {e}")
            return None, None
    
    def calculate_rsi(self, closes, period=14):
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def get_btc_data(self):
        """
        Get BTC price and RSI
        Returns: (price, rsi)
        """
        try:
            # Get current price
            ticker = self.exchange.fetch_ticker('BTC/USDT')
            price = ticker['last']
            
            # Get OHLCV for RSI
            ohlcv = self.exchange.fetch_ohlcv('BTC/USDT', '1d', limit=215)
            ohlcv = ohlcv[:-1]  # Remove incomplete candle
            closes = [x[4] for x in ohlcv]
            
            rsi = self.calculate_rsi(closes)
            
            return price, rsi
        except Exception as e:
            logger.error(f"Failed to get BTC data: {e}")
            return None, None
    
    def send_alert(self, message):
        """Send Telegram alert to all allowed users"""
        try:
            bot = Bot(token=self.bot_token)
            for user_id in self.allowed_users:
                if user_id.strip():
                    bot.send_message(
                        chat_id=user_id.strip(),
                        text=message,
                        parse_mode='Markdown'
                    )
            logger.info("Alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def check_panic(self):
        """Main check function"""
        logger.info("="*60)
        logger.info("Fear & Greed Panic Check")
        logger.info("="*60)
        
        # Get data
        fg_score, fg_class = self.get_fear_greed()
        price, rsi = self.get_btc_data()
        
        if fg_score is None or price is None:
            logger.error("Failed to get data, skipping check")
            return
        
        logger.info(f"Fear & Greed: {fg_score} ({fg_class})")
        logger.info(f"BTC Price: ${price:,.2f}")
        logger.info(f"RSI(14): {rsi:.1f}")
        
        # Check for extreme panic
        if fg_score < 10 and rsi < 25:
            level = "🚨🚨🚨 EXTREME PANIC"
            suggestion = "$1,120 (4x) ≈ NT$34,700"
        elif fg_score < 10:
            level = "🚨 EXTREME FEAR"
            suggestion = "$840-1,120 ≈ NT$26,000-34,700"
        elif fg_score < 20 and rsi < 30:
            level = "⚠️ STRONG PANIC"
            suggestion = "$840 (3x) ≈ NT$26,000"
        else:
            logger.info(f"No panic detected (F&G={fg_score}, RSI={rsi:.1f})")
            return
        
        # Send alert
        message = f"""
{level}

**Fear & Greed Index:** {fg_score} ({fg_class})
**RSI(14):** {rsi:.1f}
**BTC Price:** ${price:,.2f}

💰 **建議加倉：{suggestion}**

這是極度恐慌時刻！考慮立即加碼買入。

📅 時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        self.send_alert(message)
        logger.info(f"PANIC ALERT SENT: F&G={fg_score}, RSI={rsi:.1f}")

if __name__ == "__main__":
    try:
        detector = PanicDetector()
        detector.check_panic()
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        sys.exit(1)
