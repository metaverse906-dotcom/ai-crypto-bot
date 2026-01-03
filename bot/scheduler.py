# bot/scheduler.py
"""
Bot 排程任務
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import asyncio
from bot.handlers.dca import get_dca_analysis
from core.signal_notifier import SignalNotifier
from tools.setup_logging import setup_logging

logger = setup_logging(__name__)

class BotScheduler:
    """Bot 排程管理器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone('Asia/Taipei')
    
    def send_weekly_dca_sync(self):
        """發送每週 DCA 建議（同步包裝）"""
        try:
            asyncio.run(self._send_weekly_dca())
        except Exception as e:
            logger.error(f"❌ 發送每週 DCA 失敗: {e}")
    
    async def _send_weekly_dca(self):
        """發送每週 DCA 建議（異步）"""
        try:
            logger.info("📅 開始生成每週 DCA 建議...")
            
            from bot.handlers.dca import get_dca_analysis
            from core.signal_notifier import SignalNotifier
            
            # 獲取 DCA 分析
            message = await get_dca_analysis()
            
            # 添加自動推送標記
            auto_message = f"""
🔔 **每週 Smart DCA 自動提醒**

{message}

💡 這是每週日晚上的自動建議
隨時可用 /dca_now 手動查詢
"""
            
            # 發送給所有用戶
            notifier = SignalNotifier()
            await notifier.send_notification(auto_message, level='INFO')
            
            logger.info("✅ 每週 DCA 建議已發送")
            
        except Exception as e:
            logger.error(f"❌ 發送每週 DCA 失敗: {e}")
    def start(self):
        """啟動排程"""
        # 每週日晚上 8:00（台北時間）
        self.scheduler.add_job(
            self.send_weekly_dca_sync,  # 使用同步包裝版本
            CronTrigger(
                day_of_week='sun',  # 週日
                hour=20,            # 晚上 8 點
                minute=0,
                timezone=self.timezone
            ),
            id='weekly_dca',
            name='每週 DCA 建議',
            replace_existing=True
        )
        
        logger.info("📅 排程已設定：")
        logger.info("  - 每週日 20:00（台北時間）：DCA 建議推送")
        
        self.scheduler.start()
        logger.info("✅ 排程器已啟動")
    
    def stop(self):
        """停止排程"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏹️ 排程器已停止")
