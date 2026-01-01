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
    獲取 DCA 分析（F&G Enhanced版本）
    Returns: 格式化的分析訊息
    """
    # 獲取 BTC 數據（修正：移除未收盤K線）
    symbol = 'BTC/USDT'
    ticker = await asyncio.to_thread(exchange.fetch_ticker, symbol)
    ohlcv = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, '1d', limit=201)
    
    # ✅ 移除最後一根未收盤的K線（避免RSI跳動）
    ohlcv = ohlcv[:-1]
    
    # 計算簡單的 RSI 和 MA
    closes = [candle[4] for candle in ohlcv]
    current_price = ticker['last']
    
    # 獲取 Fear & Greed 指數
    try:
        import requests
        fg_response = requests.get("https://api.alternative.me/fng/", timeout=10)
        fg_data = fg_response.json()
        fg_score = int(fg_data['data'][0]['value'])
        fg_class = fg_data['data'][0]['value_classification']
    except:
        fg_score = None
        fg_class = "無法獲取"
    
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
    
    # === F&G Enhanced 買入邏輯 ===
    
    # 決定買入金額（每月投入$30-40k TWD → 每週約$280 USD）
    base_amount = 280  # 每週基礎金額 USD
    
    if fg_score is not None and fg_score < 10 and rsi < 25:
        recommendation = "🟢🟢🟢🟢 **極度恐慌 - ALL-IN**"
        suggested_amount = "$1,120 (4x) ≈ NT$34,700"
        reason = f"F&G極低 ({fg_score}) + RSI超賣 ({rsi:.1f}) - 千載難逢機會"
    elif fg_score is not None and fg_score < 20 and rsi < 30:
        recommendation = "🟢🟢🟢 **強烈恐慌 - 大力加碼**"
        suggested_amount = "$840 (3x) ≈ NT$26,000"
        reason = f"F&G極度恐慌 ({fg_score}) + RSI恐慌 ({rsi:.1f})"
    elif fg_score is not None and fg_score < 30:
        recommendation = "🟢🟢 **市場恐慌 - 加碼買入**"
        suggested_amount = "$560 (2x) ≈ NT$17,400"
        reason = f"F&G恐慌 ({fg_score}) - 好買點"
    elif rsi < 30:
        recommendation = "🟢 **RSI恐慌 - 適度加碼**"
        suggested_amount = "$420 (1.5x) ≈ NT$13,000"
        reason = f"RSI恐慌 ({rsi:.1f}) - 技術面超賣"
    elif rsi > 70 and (fg_score is None or fg_score > 75):
        recommendation = "🟡 **市場過熱 - 觀望**"
        suggested_amount = "$280 (正常) ≈ NT$8,700"
        reason = f"RSI過高 ({rsi:.1f}), 價格昂貴 - 保持定投"
    else:
        recommendation = "🟢 **正常市場 - 定期買入**"
        suggested_amount = "$280 (1x) ≈ NT$8,700"
        reason = f"正常範圍 - 持續定投"
    
    # 組合訊息
    message = f"""
💰 **Smart DCA 本週建議（F&G Enhanced）**

{recommendation}

**市場狀態**
BTC價格：${current_price:,.2f}
RSI(14)：{rsi:.1f}
MA200：${ma200:,.2f}
"""
    
    if fg_score is not None:
        message += f"Fear & Greed：{fg_score} ({fg_class})\n"
    
    message += f"""
**分析**
{reason}

**本週建議**
{suggested_amount}

**執行策略**
• 時間：週一至週三分批執行
• 紀律：永不賣出，長期持有
• 目標：持續累積BTC

📊 數據源：OKX + Fear & Greed Index
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
