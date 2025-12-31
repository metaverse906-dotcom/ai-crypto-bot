# bot/scheduler.py
"""
Bot 排程任務
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from bot.handlers.dca import get_dca_analysis
from core.signal_notifier import SignalNotifier

logger = logging.getLogger(__name__)

class BotScheduler:
    """Bot 排程管理器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.timezone = pytz.timezone('Asia/Taipei')
        self.notifier = SignalNotifier()
        
    async def send_weekly_dca(self):
        """發送每週 DCA 建議"""
        try:
            logger.info("📅 開始生成每週 DCA 建議...")
            
            # 獲取 DCA 分析
            message = await get_dca_analysis()
            
            # 添加自動推送標記
            auto_message = f"""
🔔 **每週 Smart DCA 自動提醒**

{message}

💡 這是每週一早上的自動建議
隨時可用 /dca_now 手動查詢
"""
            
            # 發送給所有用戶
            await self.notifier.send_notification(auto_message, level='INFO')
            
            logger.info("✅ 每週 DCA 建議已發送")
            
        except Exception as e:
            logger.error(f"❌ 發送每週 DCA 失敗: {e}")
    
    def start(self):
        """啟動排程"""
        # 每週一早上 9:00（台北時間）
        self.scheduler.add_job(
            self.send_weekly_dca,
            CronTrigger(
                day_of_week='mon',  # 週一
                hour=9,
                minute=0,
                timezone=self.timezone
            ),
            id='weekly_dca',
            name='每週 DCA 建議',
            replace_existing=True
        )
        
        logger.info("📅 排程已設定：")
        logger.info("  - 每週一 09:00：DCA 建議推送")
        
        self.scheduler.start()
        logger.info("✅ 排程器已啟動")
    
    def stop(self):
        """停止排程"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏹️ 排程器已停止")
