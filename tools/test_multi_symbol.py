# tools/test_multi_symbol.py
"""
測試多幣種連接和策略
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.symbols import HYBRID_SFP_SYMBOLS
from core.execution import ExecutionSystem


async def test_connections():
    """測試所有幣種連接"""
    print("="*70)
    print("多幣種連接測試")
    print("="*70)
    
    executor = ExecutionSystem(symbol='BTC/USDT')
    
    for symbol in HYBRID_SFP_SYMBOLS:
        print(f"\n測試 {symbol}...")
        
        try:
            # 設置幣種
            executor.symbol = symbol
            await executor.connect()
            
            # 獲取數據測試
            df = await executor.fetch_ohlcv(timeframe='4h', limit=10)
            
            if df is not None and len(df) > 0:
                latest_price = df.iloc[-1]['close']
                print(f"  ✅ 連接成功")
                print(f"  📊 最新價格: ${latest_price:,.2f}")
                print(f"  📈 數據量: {len(df)} 根K線")
            else:
                print(f"  ⚠️ 無法獲取數據")
        
        except Exception as e:
            print(f"  ❌ 連接失敗: {e}")
    
    print("\n" + "="*70)
    print("測試完成")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_connections())
