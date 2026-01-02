#!/usr/bin/env python3
"""
極端機會偵測 - Cron 入口腳本
每天3次檢查MVRV極端機會（9:00, 15:00, 21:00）
"""
import sys
import os
import asyncio

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 導入並執行腳本
if __name__ == "__main__":
    from scripts.analysis.check_mvrv_panic import MVRVPanicDetector
    
    try:
        detector = MVRVPanicDetector()
        asyncio.run(detector.check_extreme_opportunity())
    except Exception as e:
        print(f"❌ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)
