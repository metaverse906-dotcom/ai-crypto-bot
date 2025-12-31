#!/usr/bin/env python3
"""
安全認證模組
"""
import time
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import ALLOWED_USERS, ADMIN_USERS

class Authenticator:
    """用戶認證管理"""
    
    def __init__(self):
        self.sessions = {}  # {user_id: last_activity_time}
        self.session_timeout = 1800  # 30 分鐘
    
    def is_authorized(self, user_id: int, level: str = 'view') -> bool:
        """
        檢查用戶權限
        
        Args:
            user_id: Telegram 用戶 ID
            level: 權限級別 (view, control, admin)
        
        Returns:
            是否有權限
        """
        if level == 'admin':
            return user_id in ADMIN_USERS
        elif level == 'control':
            return user_id in ADMIN_USERS
        elif level == 'view':
            return user_id in ALLOWED_USERS
        return False
    
    def update_session(self, user_id: int):
        """更新用戶 session"""
        self.sessions[user_id] = time.time()
    
    def is_session_valid(self, user_id: int) -> bool:
        """檢查 session 是否有效"""
        if user_id not in self.sessions:
            return False
        
        elapsed = time.time() - self.sessions[user_id]
        return elapsed < self.session_timeout
    
    def cleanup_sessions(self):
        """清理過期 session"""
        current_time = time.time()
        expired = [
            uid for uid, last_time in self.sessions.items()
            if current_time - last_time > self.session_timeout
        ]
        for uid in expired:
            del self.sessions[uid]


# 全局認證器
authenticator = Authenticator()


def require_auth(level: str = 'view'):
    """
    裝飾器：要求認證
    
    Usage:
        @require_auth('view')
        async def my_command(update, context):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            user_id = user.id
            
            # 檢查權限
            if not authenticator.is_authorized(user_id, level):
                await update.message.reply_text(
                    "❌ 無權限\n\n"
                    "此 Bot 僅供授權用戶使用。\n"
                    f"您的 User ID: {user_id}"
                )
                return
            
            # 更新 session
            authenticator.update_session(user_id)
            
            # 執行原函數
            return await func(update, context)
        
        return wrapper
    return decorator


def admin_only(func):
    """裝飾器：僅管理員可用"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USERS:
            await update.message.reply_text("❌ 此指令僅限管理員使用")
            return
        
        authenticator.update_session(user_id)
        return await func(update, context)
    
    return wrapper
