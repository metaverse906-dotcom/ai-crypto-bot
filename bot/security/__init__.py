# bot/security/__init__.py
"""
安全模組
"""
from .authenticator import authenticator, require_auth, admin_only

__all__ = ['authenticator', 'require_auth', 'admin_only']
