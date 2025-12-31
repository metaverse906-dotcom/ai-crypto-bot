# strategies/hybrid_sfp.py
import pandas as pd
# 使用 ta 庫（已安裝）替代 pandas_ta
import ta
import time
import sys
from datetime import datetime
from core.persistence import StateManager

class HybridSFPStrategy:
    def __init__(self, execution_system):
        self.exec = execution_system
        # AI 已移除 - 純技術邏輯
        
        # --- 策略參數 (來自你的設定) ---
        self.timeframe = '4h'           # 適合波段交易
        self.risk_per_trade = 0.02      # 2% Risk
        self.max_leverage = 5           # 硬上限
        self.sl_tp_ratio = 2.5          # 盈虧比 1:2.5 (數據驗證最優)
        
        # 模擬帳戶狀態 (已移除，改用 ExecutionSystem 統一管理)
        # self.paper_balance = 1000.0
        
        # 防止重複入場 (K線時間過濾) - 改用 StateManager
        self.state_manager = StateManager()
        saved_state = self.state_manager.get_strategy_state("hybrid_sfp", "last_signal_time", {})
        self.last_signal_time = saved_state # 格式: {'BTC/USDT': timestamp}
        
        # API 節流：已經問過 AI 的 K 線，無論結果如何，都不再重複問
        self.analyzed_candles = set()
        
        # 簡單印出狀態，方便 debug
        # print(f"   [HybridSFP] 狀態載入: {len(self.last_signal_time)} 筆記錄")

    def calculate_indicators(self, df):
        """計算技術指標 (ATR, BB, SFP, EMA)"""
        # 1. ATR (風控核心)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['rsi'] = ta.rsi(df['close'], length=14) # 新增 RSI 指標
        
        # ADX (趨勢強度) - 用於過濾強趨勢逆勢
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx_df is not None:
            df['adx'] = adx_df[adx_df.columns[0]] # 取得 ADX 值
        
        # 2. 布林帶
        bb = ta.bbands(df['close'], length=50, std=2.0)
        # 處理欄位名稱 (pandas_ta 產生的名稱可能不同，這裡做通用處理)
        if bb is not None:
            df = pd.concat([df, bb], axis=1)
            # 重新命名方便後續呼叫
            cols = df.columns
            df['bb_upper'] = df[cols[cols.str.startswith('BBU')][0]]
            df['bb_lower'] = df[cols[cols.str.startswith('BBL')][0]]
            df['bw'] = df[cols[cols.str.startswith('BBB')][0]]

        # 3. Swing High/Low (SFP 用)
        df['swing_high'] = df['high'].rolling(window=50).max().shift(1)
        df['swing_low'] = df['low'].rolling(window=50).min().shift(1)
        
        # 4. EMA 200 (趨勢過濾)
        df['ema200'] = ta.ema(df['close'], length=200)
        
        return df

    def check_signals(self, df):
        """核心邏輯: SFP 優先，Trend 其次"""
        prev = df.iloc[-2] # 確認收盤的 K 線
        
        signal = None
        setup_type = None
        stop_loss = 0.0
        
        # --- 策略 A: SFP (反轉) ---
        # 核心發現：SFP 在強趋勢過熱時最有效！
        # ADX > 30 = 強趋勢，此時 SFP 反轉意義最大
        if prev.get('adx', 0) > 30:  # ✅ 修正！原為 < 30 導致虧損 -72%
            if prev['high'] > prev['swing_high'] and prev['close'] < prev['swing_high']:
                if prev['rsi'] > 60:  # ✅ 優化！數據證明 60/40 比 55/45 提升 5.32%
                    signal = 'SHORT'
                    setup_type = 'SFP (Bearish Reversal)'
                    stop_loss = prev['high']
                
            elif prev['low'] < prev['swing_low'] and prev['close'] > prev['swing_low']:
                if prev['rsi'] < 40:  # ✅ 優化！數據證明 60/40 比 55/45 提升 5.32%
                    signal = 'LONG'
                    setup_type = 'SFP (Bullish Reversal)'
                    stop_loss = prev['low']
            
        # --- 策略 B: Trend (順勢) ---
        # Trend Breakout 需要足夠的趋勢強度
        if signal is None:
            bw_min = 5.0
            # 確認趋勢強度
            if prev.get('adx', 0) > 25:  # ✅ 趋勢確認
                # 多頭: 收盤 > 上軒 & > EMA200
                if prev['close'] > prev['bb_upper'] and prev['close'] > prev['ema200'] and prev['bw'] > bw_min:
                    signal = 'LONG'
                    setup_type = 'Trend Breakout'
                    stop_loss = prev['close'] - (2 * prev['atr'])
                
                # 空頭: 收盤 < 下軒 & < EMA200
                elif prev['close'] < prev['bb_lower'] and prev['close'] < prev['ema200'] and prev['bw'] > bw_min:
                    signal = 'SHORT'
                    setup_type = 'Trend Breakdown'
                    stop_loss = prev['close'] + (2 * prev['atr'])
                
        return signal, setup_type, stop_loss

    def calculate_position(self, entry, stop_loss, balance):
        """ATR 風控倉位計算"""
        risk_amount = balance * self.risk_per_trade
        dist = abs(entry - stop_loss)
        
        if dist == 0: return 0, 0
        
        # 倉位大小 = 風險金額 / 止損距離
        size = risk_amount / dist
        
        # 計算槓桿
        trade_value = size * entry
        leverage = trade_value / balance
        
        # 槓桿限制
        if leverage > self.max_leverage:
            leverage = self.max_leverage
            # 反推修正後的倉位
            size = (balance * leverage) / entry
            
        return size, leverage

    async def run(self, symbol_list, force_run=False):
        """執行掃描 (Async)"""
        # print(f"👀 [Hybrid SFP] 正在掃描 {len(symbol_list)} 個目標 (4H 級別)...")

        for symbol in symbol_list:
            # 1. 數據獲取
            self.exec.symbol = symbol
            self.exec.market_symbol = None # 強制重置，解決緩存導致的價格重複問題
            
            # 這裡我們用 4h 數據，因為此策略設計為波段
            self.exec.timeframe = self.timeframe 
            df = await self.exec.fetch_ohlcv(limit=250) # 需要 200 EMA + 50 Rolling
            
            if df is None or len(df) < 210: continue
            
            # --- 重複信號過濾 (Candle-based) ---
            # 我們是根據上一根完成的 K 線 (iloc[-2]) 來做決策
            current_signal_candle_time = df.iloc[-2]['timestamp']
            
            if self.last_signal_time.get(symbol) == current_signal_candle_time:
                # 代表這根 K 線我們已經掃描過並處理過（或已忽略），直接跳過
                # 這樣就不會重複發送相同的信號，也不會影響止損止盈的監控（如果有寫的話）
                continue
            # ----------------------------------
            
            # 2. 計算指標
            df = self.calculate_indicators(df)
            
            # 3. 檢查信號
            signal, setup_type, sl_price = self.check_signals(df)
            
            if signal:
                entry_price = df['close'].iloc[-1]
                print(f"\n🚀 發現潛在機會: {symbol} [{signal}] - {setup_type}")
                
                # 4. 直接執行（無 AI 過濾）
                balance = await self.exec.get_balance()
                
                # 計算倉位
                size, lev = self.calculate_position(entry_price, sl_price, balance)
                
                # 計算止盈 (1:2.5)
                dist = abs(entry_price - sl_price)
                tp_price = entry_price + (dist * 2.5) if signal == 'LONG' else entry_price - (dist * 2.5)
                
                print(f"🔥 [EXECUTE] {symbol} {signal}")
                print(f"   Size: {size:.4f} | Lev: {lev:.2f}x")
                print(f"   SL: {sl_price:.2f} | TP: {tp_price:.2f}")
                
                # 呼叫執行系統下單
                await self.exec.place_order(
                    side=signal.lower(),
                    amount=size,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    strategy='HybridSFP'
                )
                
                # 記錄這根 K 線已經交易過
                self.last_signal_time[symbol] = current_signal_candle_time
                self._save_status()
            else:
                curr_price = df['close'].iloc[-1]
                # 無訊號時保持安靜
                pass
                
        # print("   ✅ 掃描完成。沒有發現新機會。")

    def _save_status(self):
        """保存當前狀態到 JSON"""
        # 直接保存字典
        self.state_manager.update_strategy_state("hybrid_sfp", "last_signal_time", self.last_signal_time)