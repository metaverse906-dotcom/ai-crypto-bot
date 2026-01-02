#!/usr/bin/env python3
"""
初始化倉位管理器 - 用於現有持倉

用戶現有：0.21 BTC（視為核心倉）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.position_manager import PositionManager
from datetime import datetime

def init_existing_holdings():
    """初始化現有持倉"""
    
    # 創建 PositionManager（40% 核心倉）
    pm = PositionManager(core_ratio=0.4, data_file='data/positions.json')
    
    # 添加現有持倉（全部視為核心倉）
    # 假設平均成本 $50,000（可以改成實際成本）
    EXISTING_BTC = 0.21
    ESTIMATED_COST = 66743.81  # 修改為你的實際平均成本
    
    print(f"\n初始化現有持倉：")
    print(f"數量：{EXISTING_BTC} BTC")
    print(f"估計成本：${ESTIMATED_COST:,}")
    print(f"分類：100% 核心倉（永不賣出）\n")
    
    # 手動添加為核心倉
    pm.add_buy(
        amount=EXISTING_BTC,
        price=ESTIMATED_COST,
        note="現有持倉（初始化）",
        force_category='core'  # 強制為核心倉
    )
    
    # 顯示統計
    stats = pm.get_stats()
    print(f"✅ 初始化完成！")
    print(f"\n當前持倉：")
    print(f"  核心倉：{stats['core_btc']:.8f} BTC @ ${stats['core_avg_cost']:,.0f}")
    print(f"  交易倉：{stats['trade_btc']:.8f} BTC")
    print(f"  總持倉：{stats['total_btc']:.8f} BTC")
    print(f"\n未來新買入將按 40/60 分配。")
    print(f"數據已保存到：data/positions.json\n")

if __name__ == '__main__':
    init_existing_holdings()
