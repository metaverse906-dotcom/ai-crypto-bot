#!/usr/bin/env python3
# tools/backup_database.py
"""
資料庫自動備份腳本
每天自動備份 trading.db，保留最近 30 天
"""

import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import time


def backup_database(db_path='data/trading.db', backup_dir='data/backups'):
    """
    備份資料庫
    
    Args:
        db_path: 資料庫路徑
        backup_dir: 備份目錄
    """
    try:
        # 確保備份目錄存在
        os.makedirs(backup_dir, exist_ok=True)
        
        # 檢查資料庫是否存在
        if not os.path.exists(db_path):
            print(f"⚠️ 資料庫不存在: {db_path}")
            return
        
        # 生成備份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'trading_{timestamp}.db')
        
        # 複製資料庫
        shutil.copy2(db_path, backup_file)
        
        file_size = os.path.getsize(backup_file) / 1024 / 1024  # MB
        print(f"✅ 資料庫已備份: {backup_file} ({file_size:.2f} MB)")
        
        # 清理舊備份
        cleanup_old_backups(backup_dir, days=30)
        
    except Exception as e:
        print(f"❌ 備份失敗: {e}")


def cleanup_old_backups(backup_dir, days=30):
    """
    清理超過指定天數的備份
    
    Args:
        backup_dir: 備份目錄
        days: 保留天數
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for file in Path(backup_dir).glob('trading_*.db'):
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            
            if file_time < cutoff_date:
                file.unlink()
                deleted_count += 1
                print(f"🗑️ 刪除舊備份: {file.name}")
        
        if deleted_count > 0:
            print(f"✅ 清理完成，刪除了 {deleted_count} 個舊備份")
    
    except Exception as e:
        print(f"❌ 清理備份失敗: {e}")


def run_backup_scheduler():
    """
    運行備份排程器
    每天凌晨 3 點自動備份
    """
    print("🕐 資料庫備份排程器已啟動")
    print("   每天 03:00 自動備份")
    print("   保留最近 30 天的備份")
    print()
    
    # 立即執行一次備份
    print("執行初始備份...")
    backup_database()
    print()
    
    # 排程每天凌晨 3 點
    schedule.every().day.at("03:00").do(backup_database)
    
    # 持續運行
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        # 排程模式
        run_backup_scheduler()
    else:
        # 單次備份模式
        print("執行單次備份...")
        backup_database()
        print("\n使用 --schedule 參數啟動自動備份排程")
