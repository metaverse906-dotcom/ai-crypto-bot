#!/usr/bin/env python3
# tools/test_smart_dca_advisor.py
"""
測試Smart DCA提醒系統
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import ccxt
from strategies.smart_dca_advisor import SmartDCAAdvisor

# 創建簡單的notifier
class SimpleNotifier:
    async def send_message(self, message):
        print(f"\n{'='*70}")
        print("Telegram通知內容:")
        print(message)
        print('='*70)

async def test_advisor():
    """測試提醒系統"""
    print("="*70)
    print("測試 Smart DCA 提醒系統")
    print("="*70)
    
    # 初始化
    notifier = SimpleNotifier()
    exchange = ccxt.binance()
    advisor = SmartDCAAdvisor(notifier)
    
    print("\n1. 測試市場數據獲取...")
    try:
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=10)
        print(f"✅ 成功獲取 {len(ohlcv)} 筆數據")
        print(f"   最新價格: ${ohlcv[-1][4]:,.2f}")
    except Exception as e:
        print(f"❌ 失敗: {e}")
        return
    
    print("\n2. 測試建議生成...")
    try:
        advice = await advisor.weekly_analysis(exchange)
        print("✅ 建議生成成功")
        print(f"\n當前市場狀況:")
        print(f"  BTC價格: ${advice['price']:,.2f}")
        print(f"  RSI: {advice['rsi']:.2f}")
        print(f"  MA200: ${advice['ma200']:,.2f}")
        print(f"\n建議操作:")
        print(f"  買入金額: ${advice['buy_amount']:.0f}")
        print(f"  買入理由: {advice['buy_reason']}")
        if advice['sell_signal']:
            print(f"  ⚠️ 賣出信號: {advice['sell_amount']:.6f} BTC")
    except Exception as e:
        print(f"❌ 失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n3. 測試狀態保存...")
    try:
        advisor.save_state()
        print("✅ 狀態保存成功")
        print(f"   文件位置: {advisor.state_file}")
    except Exception as e:
        print(f"❌ 失敗: {e}")
    
    print("\n" + "="*70)
    print("測試完成！")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_advisor())
