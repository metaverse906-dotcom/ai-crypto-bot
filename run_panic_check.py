#!/usr/bin/env python3
"""
恐慌檢測 - Cron 入口腳本
用於 Crontab 執行，路徑已更新
"""
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 導入並執行腳本
if __name__ == "__main__":
    from scripts.analysis.check_fg_panic import PanicDetector
    
    try:
        detector = PanicDetector()
        detector.check_panic()
    except Exception as e:
        print(f"❌ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)
