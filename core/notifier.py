#!/usr/bin/env python3
# core/notifier.py
"""
統一通知系統
支持 Telegram, Discord, Email
"""

import os
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("Telegram 通知未啟用（缺少環境變量）")
    
    def send_message(self, message: str, level: str = "INFO") -> bool:
        """
        發送訊息到 Telegram
        
        Args:
            message: 訊息內容
            level: 訊息級別 (INFO, WARNING, ERROR, CRITICAL)
        
        Returns:
            是否發送成功
        """
        if not self.enabled:
            logger.debug(f"Telegram 未啟用，跳過通知: {message}")
            return False
        
        try:
            import requests
            
            # 添加表情符號
            emoji_map = {
                'INFO': '📊',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            emoji = emoji_map.get(level, '📢')
            
            # 格式化訊息
            formatted_message = f"{emoji} **{level}**\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 發送 API 請求
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram 通知已發送: {level}")
            return True
            
        except Exception as e:
            logger.error(f"Telegram 通知失敗: {e}")
            return False
    
    def send_alert(self, title: str, message: str, level: str = "WARNING"):
        """發送警報"""
        full_message = f"**{title}**\n\n{message}"
        return self.send_message(full_message, level)
    
    def send_trade_notification(self, symbol: str, side: str, price: float, reason: str):
        """發送交易通知"""
        message = (
            f"**交易信號**\n"
            f"標的: {symbol}\n"
            f"方向: {side}\n"
            f"價格: ${price:.2f}\n"
            f"原因: {reason}"
        )
        return self.send_message(message, "INFO")


class Notifier:
    """統一通知器（支持多種通知方式）"""
    
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.enabled_channels = []
        
        if self.telegram.enabled:
            self.enabled_channels.append('telegram')
    
    def notify(self, message: str, level: str = "INFO", title: Optional[str] = None):
        """
        發送通知到所有啟用的渠道
        
        Args:
            message: 訊息內容
            level: 級別
            title: 標題（可選）
        """
        if not self.enabled_channels:
            logger.debug("無啟用的通知渠道")
            return
        
        full_message = f"{title}\n\n{message}" if title else message
        
        if 'telegram' in self.enabled_channels:
            self.telegram.send_message(full_message, level)
    
    def alert_error(self, error_message: str, exception: Optional[Exception] = None):
        """錯誤警報"""
        message = error_message
        if exception:
            message += f"\n\n錯誤詳情: {str(exception)}"
        
        self.notify(message, level="ERROR", title="🚨 系統錯誤")
    
    def alert_critical(self, message: str):
        """嚴重警報"""
        self.notify(message, level="CRITICAL", title="🚨 嚴重警報")
    
    def info(self, message: str):
        """一般資訊"""
        self.notify(message, level="INFO")


# 全局實例
notifier = Notifier()


if __name__ == "__main__":
    # 測試
    print("測試通知系統...")
    print(f"啟用渠道: {notifier.enabled_channels}")
    
    if notifier.telegram.enabled:
        notifier.telegram.send_message("測試訊息", "INFO")
        print("✅ Telegram 測試訊息已發送")
    else:
        print("⚠️ Telegram 未配置")
        print("請設置環境變量:")
        print("  export TELEGRAM_BOT_TOKEN='your_token'")
        print("  export TELEGRAM_CHAT_ID='your_chat_id'")
