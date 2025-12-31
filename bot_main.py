#!/usr/bin/env python3
"""
Bot 啟動腳本
"""
from bot.telegram_bot import main

if __name__ == "__main__":
    print("="*60)
    print("🤖 Crypto Trading Telegram Bot")
    print("="*60)
    print()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot 已停止")
    except Exception as e:
        print(f"\n❌ 錯誤：{e}")
