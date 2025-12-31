#!/usr/bin/env python3
# strategies/smart_dca_advisor.py
"""
Smart DCA 提醒系統
每週提供買入/賣出建議，由用戶手動執行
"""

import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import json
import os
import asyncio

class SmartDCAAdvisor:
    def __init__(self, notifier):
        self.notifier = notifier
        self.state_file = 'data/smart_dca_state.json'
        self.load_state()
    
    def load_state(self):
        """載入狀態"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'btc_holdings': 0,
                'usdt_reserve': 0,
                'total_invested': 0,
                'last_check': None,
                'history': []
            }
    
    def save_state(self):
        """保存狀態"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    async def weekly_analysis(self, exchange):
        """每週分析並生成建議"""
        try:
            # 獲取數據（ccxt同步調用）
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 計算指標
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ma200'] = ta.sma(df['close'], length=200)
            
            current_price = df.iloc[-1]['close']
            current_rsi = df.iloc[-1]['rsi']
            current_ma200 = df.iloc[-1]['ma200']
            
            # 檢查數據有效性
            if pd.isna(current_rsi):
                raise ValueError("RSI數據無效")
            
            # 生成建議
            advice = self.generate_advice(current_price, current_rsi, current_ma200)
            
            # 發送通知
            await self.send_weekly_notification(advice)
            
            # 更新狀態
            self.state['last_check'] = datetime.now().isoformat()
            self.save_state()
            
            return advice
            
        except Exception as e:
            error_msg = f"❌ Smart DCA 分析失敗: {str(e)}"
            print(error_msg)
            await self.notifier.send_message(error_msg)
            raise
    
    def generate_advice(self, price, rsi, ma200):
        """生成交易建議"""
        base_amount = 250
        buy_amount = base_amount
        sell_signal = False
        sell_amount = 0
        
        # 買入建議
        if rsi < 25:
            buy_amount = base_amount * 2
            buy_reason = f"RSI {rsi:.1f}（極度超賣），建議加碼2x"
        elif rsi < 35:
            buy_amount = base_amount * 1.5
            buy_reason = f"RSI {rsi:.1f}（偏低），建議加碼1.5x"
        elif rsi > 75:
            buy_amount = base_amount * 0.7
            buy_reason = f"RSI {rsi:.1f}（超買），建議減少買入"
        else:
            buy_reason = f"RSI {rsi:.1f}（正常），建議正常買入"
        
        # 儲備動用建議
        reserve_use = 0
        reserve_reason = ""
        if self.state['usdt_reserve'] > 0:
            if rsi < 25:
                reserve_use = min(self.state['usdt_reserve'] * 0.8, base_amount * 2)
                reserve_reason = f"極度超賣，建議動用儲備80%（${reserve_use:.0f}）"
            elif rsi < 30:
                reserve_use = min(self.state['usdt_reserve'] * 0.6, base_amount)
                reserve_reason = f"超賣，建議動用儲備60%（${reserve_use:.0f}）"
            elif rsi < 40:
                reserve_use = min(self.state['usdt_reserve'] * 0.4, base_amount * 0.5)
                reserve_reason = f"偏低，建議動用儲備40%（${reserve_use:.0f}）"
            else:
                reserve_reason = f"RSI未達40以下，暫不動用儲備"
        
        # 賣出建議
        if self.state['btc_holdings'] > 0 and ma200 > 0:
            sell_threshold = ma200 * 1.3
            if rsi > 75 and price > sell_threshold:
                sell_signal = True
                sell_amount = self.state['btc_holdings'] * 0.3
                sell_value = sell_amount * price
                sell_reason = f"RSI {rsi:.1f} (>75) 且價格 ${price:.0f} (>MA200*1.3=${sell_threshold:.0f})"
            else:
                rsi_gap = 75 - rsi
                price_gap = ((sell_threshold - price) / price) * 100
                sell_reason = f"未達賣出條件（RSI還差{rsi_gap:.1f}點 或 價格還差{price_gap:.1f}%）"
        
        return {
            'price': price,
            'rsi': rsi,
            'ma200': ma200,
            'buy_amount': buy_amount + reserve_use,
            'buy_base': buy_amount,
            'buy_reason': buy_reason,
            'reserve_use': reserve_use,
            'reserve_reason': reserve_reason,
            'sell_signal': sell_signal,
            'sell_amount': sell_amount,
            'sell_value': sell_amount * price if sell_signal else 0,
            'sell_reason': sell_reason if 'sell_reason' in locals() else '',
            'current_btc': self.state['btc_holdings'],
            'current_usdt': self.state['usdt_reserve']
        }
    
    async def send_weekly_notification(self, advice):
        """發送每週通知"""
        message = f"""
📊 **Smart DCA 本週建議**

**市場狀況**：
• BTC價格：${advice['price']:,.0f}
• 本週RSI：{advice['rsi']:.1f}
• MA200：${advice['ma200']:,.0f}
• 價格位置：{((advice['price']/advice['ma200']-1)*100):.1f}% {'高於' if advice['price']>advice['ma200'] else '低於'} MA200

**買入建議**：
{'✅' if advice['buy_amount'] >= 250 else '⚠️'} **建議買入：${advice['buy_amount']:.0f}**
• 基礎：${advice['buy_base']:.0f}
• 理由：{advice['buy_reason']}
{f"• 動用儲備：${advice['reserve_use']:.0f}" if advice['reserve_use'] > 0 else ""}
{f"• {advice['reserve_reason']}" if advice['reserve_reason'] else ""}

**當前持倉**：
• BTC：{advice['current_btc']:.6f}
• USDT儲備：${advice['current_usdt']:,.2f}

**賣出建議**：
{'🚨 **建議賣出**' if advice['sell_signal'] else '❌ 暫不賣出'}
{f"• 賣出數量：{advice['sell_amount']:.6f} BTC" if advice['sell_signal'] else ""}
{f"• 預計獲得：${advice['sell_value']:,.2f} USDT" if advice['sell_signal'] else ""}
• {advice.get('sell_reason', '')}

**下週準備**：
{'⚠️ 建議提前入金' if advice['buy_amount'] > 500 else '⚪ 無需提前入金'}
• 下次檢查：{(datetime.now() + timedelta(days=7)).strftime('%Y/%m/%d')}
        """.strip()
        
        await self.notifier.send_message(message)
    
    def record_action(self, action_type, amount, price):
        """記錄用戶操作"""
        self.state['history'].append({
            'date': datetime.now().isoformat(),
            'type': action_type,
            'amount': amount,
            'price': price
        })
        
        if action_type == 'buy':
            self.state['btc_holdings'] += amount / price
            self.state['total_invested'] += amount
        elif action_type == 'sell':
            self.state['btc_holdings'] -= amount
            self.state['usdt_reserve'] += amount * price
        
        self.save_state()


# 使用範例
async def run_weekly_advisor():
    """每週日早上8點執行"""
    from core.notifier import UnifiedNotifier
    import ccxt
    
    notifier = UnifiedNotifier()
    exchange = ccxt.binance()
    
    advisor = SmartDCAAdvisor(notifier)
    advice = await advisor.weekly_analysis(exchange)
    
    print("建議已發送到Telegram")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_weekly_advisor())
