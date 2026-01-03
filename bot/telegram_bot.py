#!/usr/bin/env python3
"""
Telegram Bot 主程式
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from .config import TELEGRAM_BOT_TOKEN, USE_WEBHOOK, WEBHOOK_URL, BOT_PORT
from .handlers import (
    start_command,
    help_command,
    status_command,
    emergency_stop_command,
    market_command,
    positions_command,
    settings_command,
    dca_now_command
)
from tools.setup_logging import setup_logging

# 設定日誌
logger = setup_logging(__name__)


class CryptoTradingBot:
    """加密貨幣交易 Telegram Bot"""
    
    def __init__(self):
        self.app = None
    
    async def setup_handlers(self):
        """設定指令處理器"""
        # 基礎指令
        self.app.add_handler(CommandHandler("start", start_command))
        self.app.add_handler(CommandHandler("help", help_command))
        self.app.add_handler(CommandHandler("status", status_command))
        
        # 管理員指令
        self.app.add_handler(CommandHandler("emergency_stop", emergency_stop_command))

        # 新增的指令
        self.app.add_handler(CommandHandler('market', market_command))
        self.app.add_handler(CommandHandler('positions', positions_command))
        self.app.add_handler(CommandHandler('settings', settings_command))
        self.app.add_handler(CommandHandler('dca_now', dca_now_command))
        
        # 選單按鈕處理器
        from bot.handlers.menu import button_callback
        self.app.add_handler(CallbackQueryHandler(button_callback))
        
        logger.info("✅ 指令處理器已註冊")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """錯誤處理"""
        logger.error(f"更新 {update} 發生錯誤：{context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ 發生錯誤，請稍後再試"
            )
    
    async def run_polling(self):
        """啟動 Bot（Polling 模式）"""
        logger.info("🤖 正在啟動 Crypto Trading Bot...")
        
        # 創建 Application
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # 設定處理器
        await self.setup_handlers()
        
        # 錯誤處理
        self.app.add_error_handler(self.error_handler)
        
        logger.info("🔄 Polling 模式")
        
        # 初始化並啟動（增加超時時間）
        logger.info("正在連接 Telegram...")
        await self.app.initialize()
        
        # 設定 Bot 指令菜單
        from telegram import BotCommand
        commands = [
            BotCommand("start", "🏠 主選單"),
            BotCommand("dca_now", "📊 DCA 建議"),
            BotCommand("market", "📈 市場狀態"),
            BotCommand("positions", "💼 當前倉位"),
            BotCommand("status", "System 系統狀態"),
            BotCommand("settings", "⚙️ 設定"),
            BotCommand("help", "ℹ️ 幫助")
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info("✅ Bot 指令菜單已更新")

        await self.app.start()
        
        logger.info("開始接收訊息...")
        await self.app.updater.start_polling(
            poll_interval=5.0,      # 增加輪詢間隔
            timeout=30,              # 增加超時到 30 秒
            read_timeout=30,         # 讀取超時 30 秒
            write_timeout=30,        # 寫入超時 30 秒
            connect_timeout=30,      # 連接超時 30 秒
            pool_timeout=30,         # 池超時 30 秒
            drop_pending_updates=True
        )
        
        logger.info("✅ Bot 已啟動，按 Ctrl+C 停止")
        
        # 保持運行
        try:
            import asyncio
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("正在停止 Bot...")
        finally:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()


def main():
    """主函數"""
    bot = CryptoTradingBot()
    
    import asyncio
    try:
        asyncio.run(bot.run_polling())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot 已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot 已停止")
