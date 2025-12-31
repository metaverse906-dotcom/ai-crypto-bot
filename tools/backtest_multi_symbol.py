#!/usr/bin/env python3
# tools/backtest_multi_symbol.py
"""
多幣種 Hybrid SFP 回測
模擬 5 個幣種同時運行，風控限制：最多 3 個同時倉位
"""

import pandas as pd
import pandas_ta as ta
import random
from datetime import datetime

# 5 個幣種
SYMBOLS = ['BTC', 'ETH', 'BNB', 'SOL', 'MATIC']
MAX_POSITIONS = 3


class MultiSymbolBacktest:
    """多幣種回測"""
    
    def __init__(self):
        self.active_positions = {}  # {symbol: {entry, sl, tp, ...}}
        self.closed_trades = []
        self.current_date = None
    
    def load_data(self, symbol):
        """載入數據（使用 BTC 數據模擬所有幣種）"""
        try:
            df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 轉換為 4h
            df.set_index('timestamp', inplace=True)
            df_4h = df.resample('4H').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            df_4h.reset_index(inplace=True)
            
            return df_4h
        except:
            return None
    
    def check_signal(self, df, i):
        """檢查 Hybrid SFP 信號（簡化版）"""
        if i < 50:
            return None
        
        # 計算指標
        df['ema_200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
        
        prev = df.iloc[i-1]
        
        # 檢查 ADX
        if pd.isna(prev.get('adx')) or prev['adx'] < 25:
            return None
        
        # 計算 swing high/low
        swing_high = df.iloc[max(0,i-50):i]['high'].max()
        swing_low = df.iloc[max(0,i-50):i]['low'].min()
        
        signal = None
        sl = None
        tp = None
        
        # SFP 檢測
        if prev['high'] > swing_high and prev['close'] < swing_high:
            if prev['rsi'] > 60:
                signal = 'SHORT'
                sl = prev['high']
                tp = prev['close'] - (prev['high'] - prev['close']) * 2.5
        
        elif prev['low'] < swing_low and prev['close'] > swing_low:
            if prev['rsi'] < 40:
                signal = 'LONG'
                sl = prev['low']
                tp = prev['close'] + (prev['close'] - prev['low']) * 2.5
        
        if signal:
            return {
                'signal': signal,
                'entry': prev['close'],
                'sl': sl,
                'tp': tp
            }
        
        return None
    
    def can_open_position(self):
        """檢查是否可以開新倉"""
        return len(self.active_positions) < MAX_POSITIONS
    
    def check_exits(self, symbol, current_candle):
        """檢查現有倉位是否出場"""
        if symbol not in self.active_positions:
            return
        
        pos = self.active_positions[symbol]
        
        if pos['signal'] == 'LONG':
            if current_candle['low'] <= pos['sl']:
                pnl = ((pos['sl'] - pos['entry']) / pos['entry']) * 100
                self.close_trade(symbol, pos['sl'], 'SL', pnl)
            elif current_candle['high'] >= pos['tp']:
                pnl = ((pos['tp'] - pos['entry']) / pos['entry']) * 100
                self.close_trade(symbol, pos['tp'], 'TP', pnl)
        
        else:  # SHORT
            if current_candle['high'] >= pos['sl']:
                pnl = ((pos['entry'] - pos['sl']) / pos['entry']) * 100
                self.close_trade(symbol, pos['sl'], 'SL', pnl)
            elif current_candle['low'] <= pos['tp']:
                pnl = ((pos['entry'] - pos['tp']) / pos['entry']) * 100
                self.close_trade(symbol, pos['tp'], 'TP', pnl)
    
    def close_trade(self, symbol, exit_price, reason, pnl):
        """平倉"""
        pos = self.active_positions[symbol]
        self.closed_trades.append({
            'symbol': symbol,
            'signal': pos['signal'],
            'entry': pos['entry'],
            'exit': exit_price,
            'pnl': pnl,
            'reason': reason,
            'entry_time': pos['entry_time'],
            'exit_time': self.current_date
        })
        del self.active_positions[symbol]
    
    def run(self):
        """運行多幣種回測"""
        print("="*70)
        print("多幣種 Hybrid SFP 回測")
        print("="*70)
        print(f"幣種: {SYMBOLS}")
        print(f"最大同時倉位: {MAX_POSITIONS}\n")
        
        # 載入所有數據
        data = {}
        for symbol in SYMBOLS:
            df = self.load_data(symbol)
            if df is not None:
                data[symbol] = df
                print(f"✅ {symbol}: {len(df)} 根K線")
        
        if not data:
            print("❌ 無數據")
            return
        
        # 獲取最短數據長度
        min_len = min(len(df) for df in data.values())
        
        print(f"\n開始回測... (共 {min_len} 根K線)\n")
        
        # 主循環
        for i in range(250, min_len):
            # 更新當前日期
            self.current_date = data[SYMBOLS[0]].iloc[i]['timestamp']
            
            # 1. 檢查所有現有倉位是否出場
            for symbol in list(self.active_positions.keys()):
                current_candle = data[symbol].iloc[i]
                self.check_exits(symbol, current_candle)
            
            # 2. 檢查新信號（按幣種順序）
            for symbol in SYMBOLS:
                # 檢查風控
                if not self.can_open_position():
                    break
                
                # 如果已有此幣種倉位，跳過
                if symbol in self.active_positions:
                    continue
                
                # 檢查信號
                signal_data = self.check_signal(data[symbol], i)
                
                if signal_data:
                    # 開倉
                    self.active_positions[symbol] = {
                        **signal_data,
                        'entry_time': data[symbol].iloc[i-1]['timestamp']
                    }
        
        # 統計結果
        self.print_results()
    
    def print_results(self):
        """輸出結果"""
        if not self.closed_trades:
            print("\n❌ 無交易")
            return
        
        df = pd.DataFrame(self.closed_trades)
        wins = len(df[df['pnl'] > 0])
        
        print("\n" + "="*70)
        print("回測結果")
        print("="*70)
        
        print(f"\n【總體統計】")
        print(f"  總交易: {len(df)}")
        print(f"  獲利: {wins}, 虧損: {len(df) - wins}")
        print(f"  勝率: {wins/len(df)*100:.1f}%")
        print(f"  總盈虧: {df['pnl'].sum():.2f}%")
        print(f"  平均盈虧: {df['pnl'].mean():.2f}%")
        
        print(f"\n【分幣種統計】")
        for symbol in SYMBOLS:
            symbol_trades = df[df['symbol'] == symbol]
            if len(symbol_trades) > 0:
                symbol_wins = len(symbol_trades[symbol_trades['pnl'] > 0])
                print(f"  {symbol}: {len(symbol_trades)} 筆, "
                      f"勝率 {symbol_wins/len(symbol_trades)*100:.1f}%, "
                      f"盈虧 {symbol_trades['pnl'].sum():.2f}%")
        
        print(f"\n【出場原因】")
        tp_count = len(df[df['reason'] == 'TP'])
        sl_count = len(df[df['reason'] == 'SL'])
        print(f"  止盈: {tp_count} ({tp_count/len(df)*100:.1f}%)")
        print(f"  止損: {sl_count} ({sl_count/len(df)*100:.1f}%)")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    backtester = MultiSymbolBacktest()
    backtester.run()
