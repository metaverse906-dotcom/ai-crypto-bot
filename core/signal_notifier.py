# core/signal_notifier.py
"""
Telegram 交易信號通知模組
發送格式化的交易建議到 Telegram
"""
import os
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv
import asyncio

load_dotenv()

class SignalNotifier:
    """交易信號通知器"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_ids = [int(id) for id in os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',') if id]
        
        if not self.bot_token:
            raise ValueError("未設定 TELEGRAM_BOT_TOKEN")
        
        self.bot = Bot(token=self.bot_token)
    
    async def send_signal(self, signal_data):
        """
        發送交易信號通知
        
        Args:
            signal_data (dict): 信號資料
                - symbol: 幣種
                - direction: LONG/SHORT
                - signal_type: 信號類型
                - current_price: 當前價格
                - entry_price: 建議入場價
                - stop_loss: 止損價
                - take_profit: 止盈目標
                - indicators: 技術指標
        """
        message = self._format_signal(signal_data)
        
        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                print(f"✅ 信號已發送到 {chat_id}")
            except Exception as e:
                print(f"❌ 發送失敗 {chat_id}: {e}")
    
    def _format_signal(self, data):
        """格式化信號訊息"""
        direction_emoji = "🟢" if data['direction'] == 'LONG' else "🔴"
        
        # 計算風險報酬比
        entry = data.get('entry_price', data['current_price'])
        sl = data['stop_loss']
        tp = data.get('take_profit', {})
        
        risk = abs((entry - sl) / entry * 100)
        reward = abs((tp.get('tp1', entry) - entry) / entry * 100) if tp else 0
        rr_ratio = reward / risk if risk > 0 else 0
        
        message = f"""
{direction_emoji} **Hybrid SFP 交易信號**

**幣種**: {data['symbol']}
**方向**: {data['direction']}
**類型**: {data['signal_type']}

📊 **價格資訊**
當前價格: ${data['current_price']:,.2f}
建議入場: ${entry:,.2f}

🛡️ **風險控制**
止損 (SL): ${sl:,.2f} (-{risk:.2f}%)
"""
        
        # 止盈目標
        if tp:
            message += f"""止盈目標:
  TP1: ${tp.get('tp1', 0):,.2f} (+{abs((tp.get('tp1', entry) - entry) / entry * 100):.2f}%)
  TP2: ${tp.get('tp2', 0):,.2f} (+{abs((tp.get('tp2', entry) - entry) / entry * 100):.2f}%)

風險報酬比: 1:{rr_ratio:.2f}
"""
        
        # 技術指標
        indicators = data.get('indicators', {})
        if indicators:
            message += f"""
📈 **技術指標**
ADX: {indicators.get('adx', 'N/A')}
RSI: {indicators.get('rsi', 'N/A')}
布林帶寬: {indicators.get('bb_width', 'N/A')}%
"""
        
        # 時間戳
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        return message
    
    async def send_notification(self, message, level='INFO'):
        """
        發送一般通知
        
        Args:
            message: 通知訊息
            level: INFO/WARNING/CRITICAL
        """
        emoji = {'INFO': 'ℹ️', 'WARNING': '⚠️', 'CRITICAL': '🚨'}.get(level, 'ℹ️')
        formatted_message = f"{emoji} {message}"
        
        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=formatted_message
                )
            except Exception as e:
                print(f"❌ 發送通知失敗: {e}")


# 便捷函數
async def notify_signal(signal_data):
    """發送交易信號（便捷函數）"""
    notifier = SignalNotifier()
    await notifier.send_signal(signal_data)


async def notify(message, level='INFO'):
    """發送通知（便捷函數）"""
    notifier = SignalNotifier()
    await notifier.send_notification(message, level)
