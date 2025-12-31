#!/usr/bin/env python3
"""
Bot 啟動腳本
"""
from bot.telegram_bot import main
from bot.scheduler import BotScheduler
import asyncio

if __name__ == "__main__":
    print("="*60)
    print("🤖 Crypto Trading Telegram Bot")
    print("="*60)
    print()
    
    # 啟動排程器
    scheduler = BotScheduler()
    scheduler.start()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot 已停止")
        scheduler.stop()
    except Exception as e:
        print(f"\n❌錯誤：{e}")
        scheduler.stop()
