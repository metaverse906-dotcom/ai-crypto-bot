# core/notifications.py
"""
通知系統 - 支援多種通知方式
預設關閉，需手動配置啟用
"""

import requests
import json
from datetime import datetime
from typing import Optional, Dict
import os

class NotificationManager:
    """通知管理器 - 統一介面"""
    
    def __init__(self):
        # 從配置文件讀取
        self.config = self.load_config()
        self.enabled = self.config.get('notifications_enabled', False)
    
    def load_config(self) -> Dict:
        """載入通知配置"""
        config_path = 'config/notifications.json'
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 預設配置（關閉）
        return {
            'notifications_enabled': False,
            'telegram': {
                'enabled': False,
                'bot_token': '',
                'chat_id': ''
            },
            'discord': {
                'enabled': False,
                'webhook_url': ''
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'from_email': '',
                'to_email': '',
                'password': ''
            }
        }
    
    def send_notification(self, title: str, message: str, notification_type: str = 'info'):
        """
        發送通知到所有啟用的通道
        
        Args:
            title: 通知標題
            message: 通知內容
            notification_type: 'info', 'warning', 'error', 'success'
        """
        if not self.enabled:
            return
        
        # Telegram
        if self.config.get('telegram', {}).get('enabled'):
            self.send_telegram(title, message, notification_type)
        
        # Discord
        if self.config.get('discord', {}).get('enabled'):
            self.send_discord(title, message, notification_type)
        
        # Email
        if self.config.get('email', {}).get('enabled'):
            self.send_email(title, message, notification_type)
    
    def send_telegram(self, title: str, message: str, notification_type: str):
        """發送 Telegram 通知"""
        config = self.config.get('telegram', {})
        bot_token = config.get('bot_token')
        chat_id = config.get('chat_id')
        
        if not bot_token or not chat_id:
            return
        
        # 表情符號映射
        emoji_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }
        emoji = emoji_map.get(notification_type, 'ℹ️')
        
        # 格式化消息（Markdown）
        text = f"{emoji} **{title}**\n\n{message}\n\n_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, data=data, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print(f"Telegram 通知失敗: {e}")
    
    def send_discord(self, title: str, message: str, notification_type: str):
        """發送 Discord 通知"""
        webhook_url = self.config.get('discord', {}).get('webhook_url')
        
        if not webhook_url:
            return
        
        # 顏色映射
        color_map = {
            'info': 3447003,      # 藍色
            'warning': 16776960,  # 黃色
            'error': 15158332,    # 紅色
            'success': 3066993    # 綠色
        }
        
        data = {
            'embeds': [{
                'title': title,
                'description': message,
                'color': color_map.get(notification_type, 3447003),
                'timestamp': datetime.now().isoformat()
            }]
        }
        
        try:
            response = requests.post(webhook_url, json=data, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print(f"Discord 通知失敗: {e}")
    
    def send_email(self, title: str, message: str, notification_type: str):
        """發送 Email 通知"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        config = self.config.get('email', {})
        
        if not all([config.get('from_email'), config.get('to_email'), config.get('password')]):
            return
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[交易系統] {title}"
        msg['From'] = config['from_email']
        msg['To'] = config['to_email']
        
        # HTML 內容
        html = f"""
        <html>
          <body>
            <h2>{title}</h2>
            <p>{message.replace(chr(10), '<br>')}</p>
            <hr>
            <small>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        try:
            with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['from_email'], config['password'])
                server.send_message(msg)
        except Exception as e:
            print(f"Email 通知失敗: {e}")
    
    # ==================== 預定義通知模板 ====================
    
    def notify_new_trade(self, trade_data: Dict):
        """新交易開倉通知"""
        title = "新交易開倉"
        message = f"""
品種: {trade_data.get('symbol')}
策略: {trade_data.get('strategy')}
方向: {trade_data.get('side')}
入場價格: ${trade_data.get('entry_price'):.2f}
止損: ${trade_data.get('stop_loss'):.2f}
止盈: ${trade_data.get('take_profit'):.2f}
"""
        self.send_notification(title, message, 'info')
    
    def notify_trade_closed(self, trade_data: Dict):
        """交易平倉通知"""
        pnl = trade_data.get('pnl', 0)
        notification_type = 'success' if pnl > 0 else 'error'
        
        title = "交易平倉" + (" 🎉 盈利" if pnl > 0 else " 虧損")
        message = f"""
品種: {trade_data.get('symbol')}
策略: {trade_data.get('strategy')}
方向: {trade_data.get('side')}
入場: ${trade_data.get('entry_price'):.2f}
出場: ${trade_data.get('exit_price'):.2f}
損益: ${pnl:.2f} ({trade_data.get('pnl_pct', 0):.2f}%)
原因: {trade_data.get('close_reason')}
"""
        self.send_notification(title, message, notification_type)
    
    def notify_risk_alert(self, alert_type: str, details: str):
        """風險警報通知"""
        title = f"⚠️ 風險警報: {alert_type}"
        self.send_notification(title, details, 'warning')
    
    def notify_system_error(self, error_message: str):
        """系統錯誤通知"""
        title = "系統錯誤"
        self.send_notification(title, error_message, 'error')
    
    def notify_daily_summary(self, stats: Dict):
        """每日總結通知"""
        title = "📊 每日交易總結"
        message = f"""
總交易: {stats.get('total_trades', 0)} 筆
勝: {stats.get('wins', 0)} / 敗: {stats.get('losses', 0)}
勝率: {stats.get('win_rate', 0):.1f}%
總損益: ${stats.get('total_pnl', 0):.2f}
"""
        self.send_notification(title, message, 'info')

# 全局實例（預設關閉）
notifier = NotificationManager()
