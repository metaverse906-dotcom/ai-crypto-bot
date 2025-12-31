# strategies/silver_bullet.py
import time
import sys
import pandas as pd
from datetime import datetime
import pytz
import pandas_ta as ta
from core.persistence import StateManager
from tools.smc_detector import SMCDetector

class SilverBulletStrategy:
    def __init__(self, execution_system):
        self.exec = execution_system
        # AI 已移除 - 純技術邏輯
        
        # --- 策略參數 (來自你的新代碼) ---
        self.risk_per_trade = 0.02      # 2% Risk
        self.risk_reward = 2.5          # 盈虧比 1:2.5 (數據驗證最優)
        self.daily_trade_limit = 1      # 每天只做一單 (防止過度交易)
        self.max_leverage = 10          # 最大槓桿
        
        # SMC 改為加碼機制（而非過濾）
        self.smc = SMCDetector(atr_multiplier=1.2, lookback=30)
        self.use_smc_boost = True           # 啟用 SMC 加碼
        self.smc_boost_multiplier = 1.5     # SMC 確認時倉位 +50%
        self.base_position_pct = 0.02       # 基礎倉位 2%
        
        # 狀態追蹤 (改用 StateManager)
        self.state_manager = StateManager()
        saved_state = self.state_manager.get_strategy_state("silver_bullet", "state", {})
        
        self.trades_today = saved_state.get("trades_today", 0)
        self.last_trade_date = saved_state.get("last_trade_date", None)
        
        # 為了安全起見，如果讀出來是當天但沒有次數，可能是跨日問題，交給 check_session 處理
        print(f"   [SilverBullet] 狀態載入: 最後交易日={self.last_trade_date}, 本日次數={self.trades_today}")
        print(f"   [SilverBullet] SMC 加碼: {'啟用' if self.use_smc_boost else '關閉'} (倍數={self.smc_boost_multiplier})")

    def get_ny_time(self):
        """獲取當前紐約時間"""
        utc_now = datetime.now(pytz.utc)
        ny_tz = pytz.timezone('America/New_York')
        return utc_now.astimezone(ny_tz)

    def check_session(self):
        """檢查交易時段與每日限制"""
        ny_time = self.get_ny_time()
        today_str = ny_time.strftime('%Y-%m-%d')
        
        # 1. 重置每日計數
        if self.last_trade_date != today_str:
            self.trades_today = 0
            self.last_trade_date = today_str
            # 立即保存重置後的狀態
            self._save_status()
            
        # 2. 檢查次數限制
        if self.trades_today >= self.daily_trade_limit:
            return False, "Daily limit reached"
            
        # 3. 檢查時間 (Updated Window: 10:00 AM - 13:30 PM NY Time)
        # 使用詳細的 datetime 比較，確保精確覆蓋 10:00 到 13:30
        current_time_val = ny_time.hour * 100 + ny_time.minute
        start_time_val = 1000 # 10:00
        end_time_val = 1330   # 13:30
        
        in_window = start_time_val <= current_time_val <= end_time_val
        return in_window, "In Session"

    def calculate_position(self, entry, stop_loss, balance):
        """
        動態槓桿計算 (精華部分)
        根據 2% 風險倒推倉位大小
        """
        risk_amount = balance * self.risk_per_trade
        distance = abs(entry - stop_loss)
        
        # 防呆：避免止損太近導致槓桿無限大
        if distance < (entry * 0.001): 
            distance = entry * 0.001
            
        # 計算倉位大小 (幣的數量)
        position_size = risk_amount / distance
        
        # 計算名義價值與槓桿
        notional_value = position_size * entry
        leverage = notional_value / balance
        
        # 槓桿上限保護
        if leverage > self.max_leverage:
            leverage = self.max_leverage
            # 反推縮小後的倉位
            position_size = (balance * leverage) / entry
            
        return position_size, leverage

    async def run(self, symbol_list, force_run=False):
        """
        主執行邏輯 (支援多幣種並行)
        :param symbol_list: 從 Main 傳入的動態名單 (例如 ['AT/USDT', 'BEAT/USDT'])
        """
        is_active, msg = self.check_session()
        
        if not is_active and not force_run:
            # 休眠狀態下不印任何東西，交給 main 的 dashboard 顯示
            return

        # print(f"👀 正在掃描 {len(symbol_list)} 個目標...")

        for symbol in symbol_list:
            # 1. 切換標的
            self.exec.symbol = symbol 
            try:
                await self.exec.connect() # 確保連線 (Async)
            except Exception as e:
                print(f"   連線錯誤 {symbol}: {e}")
                continue
            
            # 2. 抓取數據 (Async)
            df = await self.exec.fetch_ohlcv(limit=300)
            if df is None: continue

            # 計算 EMA 200 (趨勢濾網)
            df['ema_200'] = ta.ema(df['close'], length=200)
            
            # 計算 ATR（SMC 需要）
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            # SMC 掃描（用於加碼判斷）
            if self.use_smc_boost:
                self.smc.scan(df)
            
            # 3. 檢查形態 (Liquidity Sweep)
            # 取過去 1 小時的高低點
            last_hour_high = df['high'].iloc[-5:-1].max()
            last_hour_low = df['low'].iloc[-5:-1].min()
            current = df.iloc[-1]
            ema_val = current['ema_200']
            
            # 如果 EMA 剛開始計算還沒有值，先跳過
            if pd.isna(ema_val): continue
            
            signal = None
            stop_loss = 0
            
            # 檢測掃蕩高點 (看空) + 趨勢過濾 (價格在 EMA 之下只做空)
            if current['high'] > last_hour_high and current['close'] < last_hour_high:
                if current['close'] < ema_val:
                    signal = "SHORT"
                    stop_loss = current['high']
                
            # 檢測掃蕩低點 (看多) + 趨勢過濾 (價格在 EMA 之上只做多)
            elif current['low'] < last_hour_low and current['close'] > last_hour_low:
                if current['close'] > ema_val:
                    signal = "LONG"
                    stop_loss = current['low']
            
            # 只在有信號時執行
            if signal:
                print(f"\n🚨 {symbol} 發現潛在 {signal} 機會 (掃蕩形態)!")
                
                # 計算倉位（SMC 加碼）
                position_multiplier = 1.0
                if self.use_smc_boost:
                    ob_confirmed = self.smc.check_ob_confluence(current['close'], signal)
                    
                    if ob_confirmed:
                        position_multiplier = self.smc_boost_multiplier
                        print(f"   ✅ SMC 確認：發現 Order Block 支持，倉位加碼至 {self.base_position_pct * position_multiplier * 100:.1f}%")
                    else:
                        print(f"   ⚠️ 無 SMC 支持，使用基礎倉位 {self.base_position_pct * 100:.1f}%")
                
                # 4. 直接執行（已通過 SMC 過濾）
                balance = await self.exec.get_balance()
                entry = current['close']
                
                # 計算動態倉位
                size, lev = self.calculate_position(entry, stop_loss, balance)
                
                tp = entry - (abs(entry-stop_loss)*2.5) if signal == 'SHORT' else entry + (abs(entry-stop_loss)*2.5)
                
                print(f"🔥 [EXECUTE] {signal} {symbol}")
                print(f"   Entry: {entry} | SL: {stop_loss} | TP: {tp}")
                print(f"   Size: {size:.4f} | Lev: {lev:.1f}x")
                
                # 呼叫執行系統下單
                await self.exec.place_order(
                    side=signal.lower(),
                    amount=size,
                    stop_loss=stop_loss,
                    take_profit=tp,
                    strategy='SilverBullet'
                )
                
                self.trades_today += 1
                self._save_status()
                
                break  # 每天只做一單
        # print(f"   ✅ 掃描完成。已檢查 {len(symbol_list)} 個資產。")

    def _save_status(self):
        """保存當前狀態到 JSON"""
        state = {
            "trades_today": self.trades_today,
            "last_trade_date": self.last_trade_date
        }
        self.state_manager.update_strategy_state("silver_bullet", "state", state)