"""
Telegram Bot Menu Handlers with Inline Keyboards
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.handlers.dca import get_dca_analysis
import ccxt
import requests

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """顯示主選單"""
    keyboard = [
        [
            InlineKeyboardButton("📊 DCA 建議", callback_data='dca'),
            InlineKeyboardButton("🎯 SFP 信號", callback_data='sfp')
        ],
        [
            InlineKeyboardButton("📈 市場狀態", callback_data='market'),
            InlineKeyboardButton("ℹ️ 使用說明", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = """
🤖 **Crypto Signal Bot**

請選擇功能：

• **DCA 建議** - Fear & Greed 智能定投
• **SFP 信號** - 技術分析交易信號
• **市場狀態** - 當前市場數據
• **使用說明** - Bot 使用指南
"""
    
    # 判斷是指令還是回調
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理按鈕回調"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'dca':
        await handle_dca_button(update, context)
    elif query.data == 'sfp':
        await handle_sfp_button(update, context)
    elif query.data == 'market':
        await handle_market_button(update, context)
    elif query.data == 'help':
        await handle_help_button(update, context)
    elif query.data == 'back':
        await show_main_menu(update, context)

async def handle_dca_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 DCA 建議按鈕"""
    query = update.callback_query
    
    # 顯示載入中
    await query.edit_message_text("⏳ 正在獲取 DCA 建議...")
    
    try:
        # 獲取 DCA 分析
        analysis = await get_dca_analysis()
        
        # 添加返回按鈕
        keyboard = [[InlineKeyboardButton("🔙 返回主選單", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=analysis,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ 獲取數據失敗：{str(e)}\n\n請稍後重試。",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 返回", callback_data='back')
            ]])
        )

async def handle_sfp_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 SFP 信號按鈕"""
    query = update.callback_query
    
    message = """
🎯 **SFP 策略信號**

⚠️ **功能開發中**

此功能目前因技術限制暫時無法使用：
• Binance API 在美國地區受限
• 等待基礎設施調整

**預計包含功能**：
• Smart Money Concepts 分析
• Order Block 識別
• Fair Value Gap 檢測
• 實時交易信號推送

📅 預計上線時間：待定
"""
    
    keyboard = [[InlineKeyboardButton("🔙 返回主選單", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_market_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理市場狀態按鈕"""
    query = update.callback_query
    
    await query.edit_message_text("⏳ 正在獲取市場數據...")
    
    try:
        # 獲取市場數據
        exchange = ccxt.okx()
        ticker = exchange.fetch_ticker('BTC/USDT')
        price = ticker['last']
        change_24h = ticker['percentage']
        
        # 獲取 F&G
        try:
            fg_response = requests.get("https://api.alternative.me/fng/", timeout=5)
            fg_data = fg_response.json()
            fg_score = int(fg_data['data'][0]['value'])
            fg_class = fg_data['data'][0]['value_classification']
        except:
            fg_score = None
            fg_class = "無法獲取"
        
        # 獲取匯率
        try:
            rate_response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
            usd_to_twd = rate_response.json()['rates']['TWD']
            price_twd = round(price * usd_to_twd)
        except:
            price_twd = None
        
        message = f"""
📈 **市場狀態**

**BTC/USDT**
💰 價格：${price:,.2f}"""
        
        if price_twd:
            message += f"\n💵 台幣：NT${price_twd:,}"
        
        message += f"""
📊 24h 漲跌：{change_24h:+.2f}%
"""
        
        if fg_score is not None:
            fg_emoji = "🟢" if fg_score < 30 else "🟡" if fg_score < 70 else "🔴"
            message += f"""
**市場情緒**
{fg_emoji} Fear & Greed：{fg_score} ({fg_class})
"""
        
        message += f"""
⏰ 更新時間：{ticker['datetime']}
"""
        
        keyboard = [[InlineKeyboardButton("🔙 返回主選單", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ 獲取數據失敗：{str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 返回", callback_data='back')
            ]])
        )

async def handle_help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理使用說明按鈕"""
    query = update.callback_query
    
    message = """
ℹ️ **使用說明**

**📊 DCA 建議**
• Fear & Greed Enhanced 策略
• 根據市場恐慌程度調整投資金額
• 每週日自動推送建議
• 極度恐慌時緊急通知

**策略說明**
• 正常市場：$250/週
• 市場恐慌：2x 加碼
• 強烈恐慌：3x 加碼
• 極度恐慌：4x ALL-IN

**執行原則**
✅ 永不賣出，長期持有
✅ 週一至週三分批買入
✅ 量力而為，理性投資

**🎯 SFP 信號**
• 功能開發中
• 敬請期待

**📈 市場狀態**
• 即時 BTC 價格
• Fear & Greed 指數
• 市場情緒分析

**技術支援**
有問題請聯繫管理員

📊 數據源：OKX, Fear & Greed Index
🔒 安全：信號僅供參考，DYOR
"""
    
    keyboard = [[InlineKeyboardButton("🔙 返回主選單", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
