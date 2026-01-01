# bot/handlers/dca.py
"""
Smart DCA 相關指令處理器（優化版）
基於 Fear & Greed + RSI 的動態 DCA 建議
"""
from telegram import Update
from telegram.ext import ContextTypes
from bot.security.authenticator import require_auth
from config.dca_config import config
import ccxt
import asyncio
import requests
import pandas as pd
import pandas_ta as ta
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 交易所實例
exchange = ccxt.okx()

# 簡單的內存快取
_cache = {}


class DCAAnalysisError(Exception):
    """DCA 分析錯誤"""
    pass


async def get_fear_greed_index() -> Optional[int]:
    """
    獲取 Fear & Greed 指數（帶降級處理）
    
    Returns:
        int: Fear & Greed 分數 (0-100)
        None: 獲取失敗
    """
    try:
        response = await asyncio.to_thread(
            requests.get,
            config.fear_greed_api,
            timeout=config.api_timeout
        )
        response.raise_for_status()
        data = response.json()
        fg_score = int(data['data'][0]['value'])
        logger.info(f"Fear & Greed: {fg_score}")
        
        # 快取
        if config.enable_cache:
            _cache['fg_score'] = fg_score
            _cache['fg_time'] = asyncio.get_event_loop().time()
        
        return fg_score
    
    except Exception as e:
        logger.warning(f"獲取 Fear & Greed 失敗: {e}")
        
        # 嘗試使用快取
        if config.enable_cache and 'fg_score' in _cache:
            cache_age = asyncio.get_event_loop().time() - _cache.get('fg_time', 0)
            if cache_age < config.cache_ttl:
                logger.info(f"使用快取 Fear & Greed: {_cache['fg_score']}")
                return _cache['fg_score']
        
        return None


async def get_usd_twd_rate() -> float:
    """
    獲取 USD/TWD 匯率（帶降級處理）
    
    Returns:
        float: USD/TWD 匯率
    """
    try:
        response = await asyncio.to_thread(
            requests.get,
            config.exchange_rate_api,
            timeout=config.api_timeout
        )
        response.raise_for_status()
        rate = response.json()['rates']['TWD']
        logger.info(f"USD/TWD: {rate}")
        
        # 快取
        if config.enable_cache:
            _cache['usd_twd'] = rate
            _cache['rate_time'] = asyncio.get_event_loop().time()
        
        return rate
    
    except Exception as e:
        logger.warning(f"獲取匯率失敗: {e}")
        
        # 嘗試使用快取
        if config.enable_cache and 'usd_twd' in _cache:
            cache_age = asyncio.get_event_loop().time() - _cache.get('rate_time', 0)
            if cache_age < config.cache_ttl:
                logger.info(f"使用快取匯率: {_cache['usd_twd']}")
                return _cache['usd_twd']
        
        # 使用備用匯率
        logger.info(f"使用備用匯率: {config.default_usd_twd}")
        return config.default_usd_twd


def calculate_rsi_robust(ohlcv: list, period: int = None) -> float:
    """
    穩健的 RSI 計算（使用 pandas_ta）
    
    Args:
        ohlcv: OHLCV 數據
        period: RSI 週期
    
    Returns:
        float: RSI 值
    
    Raises:
        ValueError: RSI 計算失敗
    """
    if period is None:
        period = config.rsi_period
    
    # 轉換為 DataFrame
    df = pd.DataFrame(
        ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    
    # 移除最後一根未收盤的 K 線
    df = df[:-1]
    
    # 計算 RSI
    df['rsi'] = ta.rsi(df['close'], length=period)
    
    # 驗證
    rsi_value = df['rsi'].iloc[-1]
    if pd.isna(rsi_value):
        raise ValueError("RSI 計算失敗（NaN）")
    
    if not 0 <= rsi_value <= 100:
        raise ValueError(f"RSI 值異常: {rsi_value}")
    
    return float(rsi_value)


def calculate_ma(ohlcv: list, period: int = None) -> float:
    """
    計算移動平均
    
    Args:
        ohlcv: OHLCV 數據
        period: MA 週期
    
    Returns:
        float: MA 值
    """
    if period is None:
        period = config.ma_period
    
    df = pd.DataFrame(
        ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df = df[:-1]  # 移除未收盤
    
    ma_value = df['close'].tail(period).mean()
    return float(ma_value)


def determine_multiplier(fg_score: Optional[int], rsi: float) -> Dict[str, Any]:
    """
    決定買入倍數（核心邏輯）
    
    Args:
        fg_score: Fear & Greed 分數
        rsi: RSI 值
    
    Returns:
        dict: {
            'multiplier': float,
            'recommendation': str,
            'reason': str,
            'emoji': str
        }
    """
    # 極度恐慌（4x）
    if fg_score is not None and fg_score < config.fg_extreme_panic and rsi < config.rsi_extreme_oversold:
        return {
            'multiplier': config.multiplier_extreme,
            'recommendation': '極度恐慌 - ALL-IN',
            'reason': f'F&G極低 ({fg_score}) + RSI超賣 ({rsi:.1f}) - 千載難逢機會',
            'emoji': '🟢🟢🟢🟢'
        }
    
    # 強烈恐慌（3x）
    elif fg_score is not None and fg_score < config.fg_strong_panic and rsi < config.rsi_oversold:
        return {
            'multiplier': config.multiplier_strong,
            'recommendation': '強烈恐慌 - 大力加碼',
            'reason': f'F&G極度恐慌 ({fg_score}) + RSI恐慌 ({rsi:.1f})',
            'emoji': '🟢🟢🟢'
        }
    
    # 市場恐慌（2x）
    elif fg_score is not None and fg_score < config.fg_panic:
        return {
            'multiplier': config.multiplier_panic,
            'recommendation': '市場恐慌 - 加碼買入',
            'reason': f'F&G恐慌 ({fg_score}) - 好買點',
            'emoji': '🟢🟢'
        }
    
    # RSI 恐慌（1.5x）
    elif rsi < config.rsi_oversold:
        return {
            'multiplier': config.multiplier_rsi,
            'recommendation': 'RSI恐慌 - 適度加碼',
            'reason': f'RSI恐慌 ({rsi:.1f}) - 技術面超賣',
            'emoji': '🟢'
        }
    
    # 市場過熱（1x，觀望）
    elif rsi > config.rsi_overbought and (fg_score is None or fg_score > 75):
        return {
            'multiplier': config.multiplier_normal,
            'recommendation': '市場過熱 - 觀望',
            'reason': f'RSI過高 ({rsi:.1f}), 價格昂貴 - 保持定投',
            'emoji': '🟡'
        }
    
    # 正常市場（1x）
    else:
        return {
            'multiplier': config.multiplier_normal,
            'recommendation': '正常市場 - 定期買入',
            'reason': '正常範圍 - 持續定投',
            'emoji': '🟢'
        }


async def get_dca_analysis() -> str:
    """
    獲取 DCA 分析（優化版）
    
    Returns:
        str: 格式化的分析訊息
    
    Raises:
        DCAAnalysisError: 分析失敗
    """
    try:
        # 1. 獲取 BTC 數據
        symbol = 'BTC/USDT'
        ticker = await asyncio.to_thread(exchange.fetch_ticker, symbol)
        ohlcv = await asyncio.to_thread(
            exchange.fetch_ohlcv,
            symbol,
            '1d',
            limit=config.ohlcv_limit
        )
        
        current_price = ticker['last']
        logger.info(f"BTC Price: ${current_price:,.2f}")
        
        # 2. 計算技術指標
        rsi = calculate_rsi_robust(ohlcv)
        ma200 = calculate_ma(ohlcv, config.ma_period)
        logger.info(f"RSI: {rsi:.1f}, MA200: ${ma200:,.2f}")
        
        # 3. 獲取 Fear & Greed（可選）
        fg_score = await get_fear_greed_index()
        fg_class = "無法獲取"
        if fg_score is not None:
            if fg_score < 20:
                fg_class = "Extreme Fear"
            elif fg_score < 40:
                fg_class = "Fear"
            elif fg_score < 60:
                fg_class = "Neutral"
            elif fg_score < 80:
                fg_class = "Greed"
            else:
                fg_class = "Extreme Greed"
        
        # 4. 獲取匯率
        usd_to_twd = await get_usd_twd_rate()
        
        # 5. 決定買入倍數
        decision = determine_multiplier(fg_score, rsi)
        
        # 6. 計算金額
        usd_amt = config.base_amount_usd * decision['multiplier']
        twd_amt = round(usd_amt * usd_to_twd)
        
        # 7. 計算下次自動推送時間（週日晚上 8:00）
        from datetime import datetime, timedelta
        import pytz
        
        taipei_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(taipei_tz)
        
        # 計算下個週日
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 20:
            days_until_sunday = 7
        
        next_push = now + timedelta(days=days_until_sunday)
        next_push = next_push.replace(hour=20, minute=0, second=0, microsecond=0)
        
        # 格式化日期
        next_push_str = next_push.strftime('%m/%d（%a）晚上 8:00')
        
        # 8. 組合訊息
        message = f"""
💰 **Smart DCA 本週建議（F&G Enhanced）**

{decision['emoji']} **{decision['recommendation']}**

**市場狀態**
BTC價格：${current_price:,.2f}
RSI({config.rsi_period})：{rsi:.1f}
MA{config.ma_period}：${ma200:,.2f}
"""
        
        if fg_score is not None:
            message += f"Fear & Greed：{fg_score} ({fg_class})\n"
        
        message += f"""
**分析**
{decision['reason']}

**本週建議**
${usd_amt:.0f} ({decision['multiplier']}x) ≈ NT${twd_amt:,}

**執行策略**
• 時間：週一至週三分批執行
• 紀律：永不賣出，長期持有
• 目標：持續累積BTC

**自動排程**
📅 下次推送：{next_push_str}
🔔 固定時間：每週日晚上 8:00（台北時間）

📊 數據源：OKX + Fear & Greed Index
"""
        
        return message.strip()
    
    except Exception as e:
        logger.error(f"DCA 分析失敗: {e}", exc_info=True)
        raise DCAAnalysisError(f"分析失敗：{str(e)}")


@require_auth('view')
async def dca_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢 Smart DCA 建議 /dca_now"""
    processing_msg = None
    
    try:
        # 發送處理中訊息
        processing_msg = await update.message.reply_text("🔍 正在分析 BTC 市場...")
        
        # 獲取分析
        message = await get_dca_analysis()
        
        # 添加手動查詢時間戳
        message += "\n⏰ 查詢時間：最新數據"
        
        await processing_msg.delete()
        await update.message.reply_text(message)
        
        logger.info(f"用戶 {update.effective_user.id} 查詢 DCA 建議")
        
    except DCAAnalysisError as e:
        if processing_msg:
            await processing_msg.delete()
        await update.message.reply_text(f"❌ {str(e)}\n\n請稍後再試或聯繫管理員。")
        
    except Exception as e:
        logger.error(f"處理 /dca_now 失敗: {e}", exc_info=True)
        if processing_msg:
            await processing_msg.delete()
        await update.message.reply_text("❌ 系統錯誤，請稍後再試。")
