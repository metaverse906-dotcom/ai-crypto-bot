#!/usr/bin/env python3
# tools/setup_logging.py
"""
日誌輪轉設定模組
使用方法：from tools.setup_logging import setup_logging
        logger = setup_logging(__name__)
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(name: str, log_dir: str = 'logs', level=logging.INFO):
    """
    設定日誌輪轉
    
    Args:
        name: logger 名稱（通常是 __name__）
        log_dir: 日誌目錄
        level: 日誌級別
    
    Returns:
        configured logger
    """
    # 確保日誌目錄存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 創建 logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重複添加 handler
    if logger.handlers:
        return logger
    
    # 文件 handler（輪轉）
    log_file = os.path.join(log_dir, f'{name.replace(".", "_")}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加 handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str):
    """獲取已配置的 logger（快捷方式）"""
    return setup_logging(name)


if __name__ == "__main__":
    # 測試
    logger = setup_logging(__name__)
    logger.info("測試訊息")
    logger.warning("警告訊息")
    logger.error("錯誤訊息")
    print(f"✅ 日誌已寫入 logs/ 目錄")
