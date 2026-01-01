#!/usr/bin/env python3
"""
基礎指令處理器
"""
from telegram import Update
from telegram.ext import ContextTypes
from bot.security import require_auth, admin_only
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

@require_auth('view')
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """啟動 Bot - 顯示主選單"""
    from bot.handlers.menu import show_main_menu
    await show_main_menu(update, context)


@require_auth('view')
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """幫助指令"""
    help_text = """
📖 **指令列表**

**📊 查詢類**：
/status - 系統狀態
/positions - 當前倉位
/market <幣種> - 市場數據

**📈 Smart DCA**：
/dca_now - 當前建議

**⚙️ 設定**：
/settings - 查看設定

💡 提示：部分指令需要管理員權限
"""
    
    await update.message.reply_text(help_text)


@require_auth('view')
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢系統狀態"""
    try:
        from config.symbols import get_symbols
        
        # 使用延遲載入
        symbols = get_symbols()
        if symbols is None:
            symbols = []
        
        status_message = f"""
📊 **系統狀態**

✅ 運行中

**策略配置**：
• Hybrid SFP：監控 {len(symbols)} 個幣種
• 時間框架：4 小時
• 風險：每筆 2%

**監控幣種**：
{chr(10).join(f'• {s}' for s in symbols[:5])}
{'...' if len(symbols) > 5 else ''}
（共 {len(symbols)} 個）

⏰ 運行時間：{context.bot_data.get('uptime', '未知')}
"""
        
        await update.message.reply_text(status_message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ 錯誤：{str(e)}")


@admin_only
async def emergency_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """緊急停止（僅管理員）"""
    await update.message.reply_text(
        "⚠️ **緊急停止功能**\n\n"
        "這會停止所有交易。\n"
        "此功能暫未實作。"
    )
