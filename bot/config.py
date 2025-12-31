#!/usr/bin/env python3
"""
Telegram Bot 配置
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# 白名單（授權用戶）
ALLOWED_USERS = [int(uid) for uid in os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',') if uid]
ADMIN_USERS = [int(uid) for uid in os.getenv('TELEGRAM_ADMIN_USERS', '').split(',') if uid]

# Bot 設定
BOT_TIMEZONE = os.getenv('BOT_TIMEZONE', 'Asia/Taipei')
BOT_NOTIFY_LEVEL = os.getenv('BOT_NOTIFY_LEVEL', 'IMPORTANT')
BOT_SESSION_TIMEOUT = int(os.getenv('BOT_SESSION_TIMEOUT', '1800'))
BOT_RATE_LIMIT = int(os.getenv('BOT_RATE_LIMIT', '10'))
BOT_SILENT_MODE = os.getenv('BOT_SILENT_MODE', 'false').lower() == 'true'  # 靜默模式

# Webhook 設定
USE_WEBHOOK = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
BOT_PORT = int(os.getenv('BOT_PORT', '8000'))

# 驗證配置
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("請設定 TELEGRAM_BOT_TOKEN 環境變數")

if not ALLOWED_USERS:
    print("⚠️ 警告：未設定 TELEGRAM_ALLOWED_USERS，Bot 將拒絕所有請求")

# 啟動訊息（可選）
if not BOT_SILENT_MODE:
    print(f"✅ Bot 配置已載入")
    print(f"   授權用戶：{len(ALLOWED_USERS)} 人")
    print(f"   管理員：{len(ADMIN_USERS)} 人")
    print(f"   模式：{'Webhook' if USE_WEBHOOK else 'Polling'}")
