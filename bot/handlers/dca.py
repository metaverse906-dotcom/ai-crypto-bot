# bot/handlers/dca.py - 更新版本
"""
Smart DCA 相關指令處理器
"""
from telegram import Update
from telegram.ext import ContextTypes
from bot.security.authenticator import require_auth
import ccxt
import asyncio

exchange = ccxt.okx()


async def get_dca_analysis():
    """
    獲取 DCA 分析（可被指令和排程共用）
    Returns: 格式化的分析訊息
    """
    # 獲取 BTC 數據
    symbol = 'BTC/USDT'
    ticker = await asyncio.to_thread(exchange.fetch_ticker, symbol)
    ohlcv = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, '1d', limit=200)
    
    # 計算簡單的 RSI 和 MA
    closes = [candle[4] for candle in ohlcv]
    current_price = ticker['last']
    
    # 簡化版 RSI 計算
    def calculate_rsi(prices, period=14):
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    rsi = calculate_rsi(closes)
    ma200 = sum(closes[-200:]) / 200
    
    # 生成建議
    if rsi < 30:
        recommendation = "🟢 **強烈買入**"
        reason = f"RSI ({rsi:.1f}) 超賣，價格 (${current_price:,.0f}) 低於 MA200 (${ma200:,.0f})"
        suggested_amount = "建議：本週規劃金額的 150%"
    elif rsi < 40:
        recommendation = "🟢 **買入**"
        reason = f"RSI ({rsi:.1f}) 偏低，適合定投"
        suggested_amount = "建議：本週規劃金額"
    elif rsi > 70:
        recommendation = "🔴 **考慮減倉**"
        reason = f"RSI ({rsi:.1f}) 超買，價格 (${current_price:,.0f}) 高於 MA200"
        suggested_amount = "建議：暫停買入，考慮部分獲利"
    elif rsi > 55:
        recommendation = "🟡 **減少買入**"
        reason = f"RSI ({rsi:.1f}) 偏高"
        suggested_amount = "建議：本週規劃金額的 50%"
    else:
        recommendation = "🟢 **正常買入**"
        reason = f"RSI ({rsi:.1f}) 中性"
        suggested_amount = "建議：本週規劃金額"
    
    message = f"""
💰 **Smart DCA 本週建議**

{recommendation}

**BTC 當前狀態**
價格：${current_price:,.2f}
RSI(14)：{rsi:.1f}
MA200：${ma200:,.2f}

**分析**
{reason}

**操作建議**
{suggested_amount}

**執行時機**
建議在本週內分 2-3 次執行
避開週末波動較大時段

📊 數據源：OKX
"""
    
    return message


@require_auth('view')
async def dca_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢 Smart DCA 建議 /dca_now"""
    try:
        # 發送處理中訊息
        processing_msg = await update.message.reply_text("🔍 正在分析 BTC 市場...")
        
        # 獲取分析
        message = await get_dca_analysis()
        
        # 添加手動查詢時間戳
        message += f"\n⏰ 查詢時間：最新數據"
        
        await processing_msg.delete()
        await update.message.reply_text(message)
        
    except Exception as e:
        await processing_msg.delete()
        await update.message.reply_text(f"❌ 分析失敗：{str(e)}")
