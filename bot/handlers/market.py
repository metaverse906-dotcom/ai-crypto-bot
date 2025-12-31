# bot/handlers/market.py
"""
市場數據查詢指令處理器
"""
from telegram import Update
from telegram.ext import ContextTypes
from bot.security.authenticator import require_auth
import ccxt
import asyncio

# 使用 OKX 作為數據源
exchange = ccxt.okx()


@require_auth('view')
async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢市場數據 /market <幣種>"""
    try:
        # 解析參數
        if not context.args:
            await update.message.reply_text(
                "❌ 請提供幣種\n用法：/market BTC 或 /market ETH"
            )
            return
        
        symbol_base = context.args[0].upper()
        symbol = f"{symbol_base}/USDT"
        
        # 發送處理中訊息
        processing_msg = await update.message.reply_text(f"🔍 正在查詢 {symbol} 數據...")
        
        # 獲取市場數據
        ticker = await asyncio.to_thread(exchange.fetch_ticker, symbol)
        ohlcv = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, '4h', limit=24)
        
        # 計算 24h 變化
        change_24h = ticker.get('percentage', 0)
        volume_24h = ticker.get('quoteVolume', 0)
        
        # 計算最高最低
        high_24h = max([candle[2] for candle in ohlcv])
        low_24h = min([candle[3] for candle in ohlcv])
        
        # 格式化訊息
        message = f"""
📊 **{symbol} 市場數據**

💰 **價格**
當前：${ticker['last']:,.2f}
買價：${ticker.get('bid', 0):,.2f}
賣價：${ticker.get('ask', 0):,.2f}

📈 **24H 統計**
漲跌：{change_24h:+.2f}%
最高：${high_24h:,.2f}
最低：${low_24h:,.2f}
成交量：${volume_24h:,.0f}

⏰ 更新時間：{ticker.get('datetime', 'N/A')}
"""
        
        # 刪除處理中訊息並發送結果
        await processing_msg.delete()
        await update.message.reply_text(message)
        
    except ccxt.BadSymbol:
        await update.message.reply_text(f"❌ 找不到幣種：{symbol_base}")
    except Exception as e:
        await update.message.reply_text(f"❌ 查詢失敗：{str(e)}")


@require_auth('view')
async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢當前倉位 /positions"""
    try:
        # 由於是 Signal-Only 模式，顯示虛擬倉位或提示
        message = """
📊 **當前倉位**

ℹ️ 目前運行在信號模式
系統會發送交易建議，請手動管理倉位

如需追蹤倉位，請使用：
• Binance/OKX App
• 或記錄在筆記中

💡 未來版本將支援虛擬倉位追蹤
"""
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ 錯誤：{str(e)}")


@require_auth('view')
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看設定 /settings"""
    try:
        from config.symbols import HYBRID_SFP_SYMBOLS, get_symbols
        
        # 獲取幣種列表
        symbols = get_symbols() if callable(get_symbols) else HYBRID_SFP_SYMBOLS
        
        message = f"""
⚙️ **系統設定**

**監控幣種** ({len(symbols)}個)
{', '.join([s.split('/')[0] for s in symbols[:10]])}
{'...' if len(symbols) > 10 else ''}

**策略配置**
• 策略：Hybrid SFP
• 時間框架：4小時
• 數據源：OKX
• 模式：Signal-Only（信號通知）

**風險參數**
• 最大同時倉位：3
• 單筆倉位：2%
• 止損：根據 ATR 動態調整

**通知設定**
• Telegram 通知：✅ 啟用
• 信號級別：全部

💡 如需調整設定，請聯繫管理員
"""
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ 錯誤：{str(e)}")
