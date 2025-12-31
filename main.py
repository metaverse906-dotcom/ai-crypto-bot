# main.py
"""
Hybrid SFP 多幣種交易系統
"""
import asyncio
from datetime import datetime
from core.execution import ExecutionSystem
from strategies.hybrid_sfp import HybridSFPStrategy
from config.symbols import HYBRID_SFP_SYMBOLS, MAX_CONCURRENT_POSITIONS, MAX_PER_SYMBOL

# 通知系統（可選）
try:
    from core.notifier import notifier
except ImportError:
    class DummyNotifier:
        def notify(self, *args, **kwargs): pass
        def alert_error(self, *args, **kwargs): pass
        def alert_critical(self, *args, **kwargs): pass
    notifier = DummyNotifier()

# 倉位管理
active_positions = {}

def can_open_position(symbol):
    """檢查是否可以開新倉位"""
    if len(active_positions) >= MAX_CONCURRENT_POSITIONS:
        return False
    if symbol in active_positions and active_positions[symbol] >= MAX_PER_SYMBOL:
        return False
    return True

async def main():
    """主程序"""
    print("="*70)
    print("🤖 Hybrid SFP 多幣種交易系統 v1.0")
    print("="*70)
    print(f"監控幣種: {HYBRID_SFP_SYMBOLS}")
    print(f"最大同時倉位: {MAX_CONCURRENT_POSITIONS}")
    print(f"單幣種最大倉位: {MAX_PER_SYMBOL}")
    print("="*70)
    
    try:
        # 初始化
        executor = ExecutionSystem(symbol=HYBRID_SFP_SYMBOLS[0], timeframe='4h')
        strategy = HybridSFPStrategy(executor)
        
        print("\n🔌 正在建立連線...")
        await executor.connect(verbose=True)
        print("✅ 連線成功")
        print("✅ Hybrid SFP 策略已載入")
        
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        notifier.alert_critical(f"系統初始化失敗: {e}")
        return
    
    # 主循環
    loop_count = 0
    while True:
        try:
            loop_count += 1
            print(f"\n{'='*70}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 第 {loop_count} 輪掃描")
            print(f"{'='*70}")
            
            # 監控現有倉位
            await executor.monitor_positions()
            
            # 掃描所有幣種
            for symbol in HYBRID_SFP_SYMBOLS:
                # 檢查風控
                if not can_open_position(symbol):
                    print(f"  ⏸️  {symbol}: 倉位已滿，跳過")
                    continue
                
                try:
                    # 設置當前幣種
                    executor.symbol = symbol
                    
                    # 生成信號
                    signal = await strategy.generate_signal(symbol)
                    
                    if signal:
                        print(f"  ✅ {symbol}: 發現信號 - {signal}")
                        
                        # 執行交易
                        try:
                            # 1. 獲取餘額
                            balance = await executor.get_balance()
                            print(f"     💰 當前餘額: ${balance:.2f}")
                            
                            # 2. 獲取當前價格
                            ticker = await executor.fetch_ticker(symbol)
                            current_price = ticker['last']
                            
                            # 3. 計算倉位（策略會自動計算）
                            # signal 包含 stop_loss 和 take_profit
                            # 策略的 calculate_position 會依據餘額和風險自動計算
                            
                            # 4. 執行下單
                            side = 'buy' if signal['side'] == 'LONG' else 'sell'
                            
                            # 這裡使用策略計算的倉位大小
                            # 注意：實際下單金額由 place_order 內部的風險管理決定
                            await executor.place_order(
                                side=side,
                                amount=signal.get('size', 0.001),  # 使用信號中的倉位大小
                                stop_loss=signal.get('stop_loss'),
                                take_profit=signal.get('take_profit'),
                                strategy='Hybrid_SFP'
                            )
                            
                            # 5. 記錄倉位
                            active_positions[symbol] = active_positions.get(symbol, 0) + 1
                            print(f"     ✅ 交易已執行")
                            
                        except Exception as trade_error:
                            print(f"     ❌ 交易執行失敗: {trade_error}")
                            notifier.alert_error(f"{symbol} 交易執行失敗", str(trade_error))
                    else:
                        print(f"  ⚪ {symbol}: 無信號")
                
                except Exception as e:
                    print(f"  ❌ {symbol}: 錯誤 - {e}")
                    notifier.alert_error(f"{symbol} 掃描錯誤", str(e))
            
            print(f"\n✅ 本輪掃描完成")
            print(f"💤 等待 1 小時...")
            await asyncio.sleep(3600)
            
        except asyncio.CancelledError:
            print("\n👋 系統停止")
            await executor.close_session()
            break
        except KeyboardInterrupt:
            print("\n👋 用戶中斷")
            await executor.close_session()
            break
        except Exception as e:
            print(f"❌ 系統錯誤: {e}")
            notifier.alert_error("系統循環錯誤", str(e))
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序結束")