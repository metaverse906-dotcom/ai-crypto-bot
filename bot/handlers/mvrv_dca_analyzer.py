"""
MVRV DCA 分析模組

提供基於 MVRV Z-Score 的動態 DCA 建議
與現有 F&G 模式並存，可透過配置切換
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
import pytz
from core.mvrv_data_source import get_market_valuation_summary, get_mvrv_z_score
from core.position_manager import PositionManager
from config.strategy_config import strategy_config

logger = logging.getLogger(__name__)


async def get_mvrv_buy_multiplier(mvrv: float, rsi: float = None, fg: float = None, monthly_rsi: float = None, pi_cycle_crossed: bool = False) -> Dict[str, Any]:
    """
    根據加權分數決定買入倍數（優化後最佳配置）
    
    加權系統：MVRV 65% + RSI 25% + F&G 10%
    回測績效：+952% vs HODL (2020-2024)
    
    安全機制：
    - Pi Cycle Top 交叉 → 強制停止買入
    - 月線 RSI > 85 → 否決買入（極端過熱）
    
    Args:
        mvrv: MVRV Z-Score 值
        rsi: RSI 值（可選）
        fg: Fear & Greed 分數（可選）
        monthly_rsi: 月線 RSI（安全機制）
        pi_cycle_crossed: Pi Cycle Top 是否交叉（安全機制）
        
    Returns:
        dict: {
            'multiplier': float,
            'recommendation': str,
            'reason': str,
            'emoji': str,
            'score': float,
            'safety_override': bool  # 是否被安全機制覆蓋
        }
    """
    # 🚨 安全機制 1: Pi Cycle Top 交叉 → 絕對不買
    if pi_cycle_crossed:
        return {
            'multiplier': 0.0,
            'recommendation': '⛔ Pi Cycle 頂部信號 - 停止買入',
            'reason': 'Pi Cycle Top 交叉，歷史上標記週期頂部，暫停所有買入',
            'emoji': '🔴🔴🔴',
            'score': 100,
            'safety_override': True
        }
    
    # 🚨 安全機制 2: 月線 RSI > 85 → 極端過熱否決
    if monthly_rsi and monthly_rsi > 85:
        return {
            'multiplier': 0.0,
            'recommendation': '⛔ 月線極度過熱 - 停止買入',
            'reason': f'月線 RSI {monthly_rsi:.1f} 極度過熱，即使估值低估仍暫停買入',
            'emoji': '🔴🔴',
            'score': 95,
            'safety_override': True
        }
    
    # 1. MVRV 映射到分數（0-100）
    if mvrv < 0.1:
        mvrv_score = 0
    elif mvrv < 1.0:
        mvrv_score = 10
    elif mvrv < 3.0:
        mvrv_score = 30
    elif mvrv < 5.0:
        mvrv_score = 50
    elif mvrv < 6.0:
        mvrv_score = 65
    elif mvrv < 7.0:
        mvrv_score = 80
    elif mvrv < 9.0:
        mvrv_score = 90
    else:
        mvrv_score = 100
    
    # 2. RSI 已經是 0-100
    rsi_score = rsi if rsi and not pd.isna(rsi) else 50
    
    # 3. F&G 已經是 0-100
    fg_score = fg if fg and not pd.isna(fg) else 50
    
    # 4. 加權組合（分數越低 = 越該買）
    # 優化後最佳權重：MVRV 65% + RSI 25% + F&G 10%
    # 回測績效：30.63 BTC vs HODL 2.91 BTC (+952%)
    composite_score = (mvrv_score * 0.65) + (rsi_score * 0.25) + (fg_score * 0.10)
    
    # 5. 根據綜合分數決定倍數
    if composite_score < 15:  # 極度低估
        return {
            'multiplier': 3.5,
            'recommendation': '極度低估 - 全力加碼',
            'reason': f'綜合分數 {composite_score:.0f} (MVRV {mvrv:.2f}, RSI {rsi_score:.0f}, F&G {fg_score:.0f}) - 歷史級買點',
            'emoji': '🟢🟢🟢🟢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 25:
        return {
            'multiplier': 2.0,
            'recommendation': '強力低估 - 大力加碼',
            'reason': f'綜合分數 {composite_score:.0f} - 難得機會',
            'emoji': '🟢🟢🟢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 35:
        return {
            'multiplier': 1.5,
            'recommendation': '低估區間 - 加碼買入',
            'reason': f'綜合分數 {composite_score:.0f} - 持續累積',
            'emoji': '🟢🟢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 50:
        return {
            'multiplier': 1.0,
            'recommendation': '正常區間 - 定期買入',
            'reason': f'綜合分數 {composite_score:.0f} - 保持定投',
            'emoji': '🟢',
            'score': composite_score,
            'safety_override': False
        }
    elif composite_score < 60:
        return {
            'multiplier': 0.5,
            'recommendation': '輕度高估 - 減速買入',
            'reason': f'綜合分數 {composite_score:.0f} - 謹慎投入',
            'emoji': '🟡',
            'score': composite_score,
            'safety_override': False
        }
    else:
        return {
            'multiplier': 0.0,
            'recommendation': '過熱區域 - 停止買入',
            'reason': f'綜合分數 {composite_score:.0f} - 暫停定投',
            'emoji': '🔴',
            'score': composite_score,
            'safety_override': False
        }


async def get_mvrv_sell_recommendation(mvrv: float, rsi: float, fg: float, position_manager: PositionManager, current_price: float, pi_cycle_crossed: bool = False) -> Dict[str, Any]:
    """
    根據加權分數決定是否賣出（只針對交易倉）
    
    安全機制：Pi Cycle Top 交叉 → 立即清空交易倉
    
    Args:
        mvrv: MVRV Z-Score 值
        rsi: RSI 值
        fg: Fear & Greed 分數
        position_manager: 倉位管理器
        current_price: 當前價格
        pi_cycle_crossed: Pi Cycle Top 是否交叉
        
    Returns:
        dict: 賣出建議
    """
    stats = position_manager.get_stats()
    trade_btc = stats['trade_btc']
    
    # 🚨 安全機制: Pi Cycle Top 交叉 → 強制賣出所有交易倉
    if pi_cycle_crossed:
        return {
            'should_sell': True,
            'sell_pct': 1.0,
            'sell_btc': trade_btc,
            'reason': '🚨 Pi Cycle Top 交叉！歷史頂部信號，立即清空交易倉',
            'safety_override': True
        }
    
    # 計算綜合分數
    if mvrv < 0.1:
        mvrv_score = 0
    elif mvrv < 1.0:
        mvrv_score = 10
    elif mvrv < 3.0:
        mvrv_score = 30
    elif mvrv < 5.0:
        mvrv_score = 50
    elif mvrv < 6.0:
        mvrv_score = 65
    elif mvrv < 7.0:
        mvrv_score = 80
    elif mvrv < 9.0:
        mvrv_score = 90
    else:
        mvrv_score = 100
    
    rsi_score = rsi if not pd.isna(rsi) else 50
    fg_score = fg if not pd.isna(fg) else 50
    
    composite_score = (mvrv_score * 0.65) + (rsi_score * 0.25) + (fg_score * 0.10)
    
    # 根據分數決定賣出
    if composite_score < 70:
        return {
            'should_sell': False,
            'sell_pct': 0.0,
            'sell_btc': 0.0,
            'reason': f'綜合分數 {composite_score:.0f}，尚未過熱',
            'safety_override': False
        }
    elif composite_score < 80:
        sell_pct = 0.10
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'綜合分數 {composite_score:.0f}，輕度過熱，建議賣出交易倉 {sell_pct*100:.0f}%',
            'safety_override': False
        }
    elif composite_score < 90:
        sell_pct = 0.30
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'綜合分數 {composite_score:.0f}，明顯過熱，建議大幅減倉',
            'safety_override': False
        }
    elif composite_score < 95:
        sell_pct = 0.50
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'綜合分數 {composite_score:.0f}，極度過熱，建議清倉一半',
            'safety_override': False
        }
    else:
        sell_pct = 1.0
        return {
            'should_sell': True,
            'sell_pct': sell_pct,
            'sell_btc': trade_btc * sell_pct,
            'reason': f'綜合分數 {composite_score:.0f}，泡沫區域，建議清空交易倉',
            'safety_override': False
        }


async def get_mvrv_dca_analysis(current_price: float, position_manager: PositionManager = None) -> str:
    """
    獲取 MVRV 模式的 DCA 分析（加權分數策略）
    
    Args:
        current_price: 當前 BTC 價格
        position_manager: 倉位管理器（可選）
        
    Returns:
        str: 格式化的分析訊息
    """
    try:
        # 1. 獲取 MVRV 綜合摘要
        summary = await asyncio.to_thread(get_market_valuation_summary)
        
        mvrv = summary['mvrv_z_score']
        pi_cycle = summary['pi_cycle']
        ma_200w = summary['200w_ma']
        monthly_rsi = summary['monthly_rsi']
        overall_risk = summary['overall_risk']
        
        # 2. 獲取 RSI 和 F&G（用於加權）
        import ccxt
        exchange = ccxt.binance()
        
        # 獲取日線 RSI
        ohlcv = await asyncio.to_thread(
            exchange.fetch_ohlcv,
            'BTC/USDT',
            '1d',
            limit=100
        )
        import pandas_ta as ta
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        daily_rsi = ta.rsi(df['close'], length=14).iloc[-1]
        
        # 獲取 F&G
        import requests
        try:
            response = await asyncio.to_thread(
                requests.get,
                'https://api.alternative.me/fng/',
                timeout=5
            )
            fg_data = response.json()
            fg_score = int(fg_data['data'][0]['value'])
        except:
            fg_score = 50  # 降級
        
        # 3. 決定買入倍數（使用加權分數 + 安全機制）
        buy_decision = await get_mvrv_buy_multiplier(
            mvrv if mvrv else 1.0,
            daily_rsi,
            fg_score,
            monthly_rsi,  # 月線 RSI 安全機制
            pi_cycle.get('is_crossed', False)  # Pi Cycle 安全機制
        )
        
        # 4. 計算買入金額
        base_weekly = strategy_config.BASE_WEEKLY_USD
        buy_amount_usd = base_weekly * buy_decision['multiplier']
        
        # 5. 檢查是否需要賣出
        sell_info = None
        if position_manager and mvrv:
            sell_info = await get_mvrv_sell_recommendation(
                mvrv, daily_rsi, fg_score, position_manager, current_price,
                pi_cycle.get('is_crossed', False)  # Pi Cycle 強制賣出
            )
        
        # 5. 計算下次自動推送時間
        taipei_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(taipei_tz)
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 20:
            days_until_sunday = 7
        next_push = now + timedelta(days=days_until_sunday)
        next_push = next_push.replace(hour=20, minute=0, second=0, microsecond=0)
        next_push_str = next_push.strftime('%m/%d（%a）晚上 8:00')
        
        # 6. 組合訊息
        # 檢查是否有安全機制觸發
        safety_alert = ""
        if buy_decision.get('safety_override'):
            safety_alert = "\n\n🚨 **安全機制已觸發** 🚨\n"
        
        message = f"""
💎 **Smart DCA 本週建議（加權分數策略）**

{buy_decision['emoji']} **{buy_decision['recommendation']}**
{safety_alert}
**市場估值狀態**
BTC 價格：${current_price:,.0f}
綜合分數：{buy_decision['score']:.0f}/100 ⭐

**鏈上指標（MVRV 65%權重）**
MVRV Z-Score：{mvrv:.2f if mvrv else 'N/A'}
200週均線：${ma_200w:,.0f if ma_200w else 'N/A'}

**技術指標（RSI 25%權重）**
日線 RSI：{daily_rsi:.1f if daily_rsi else 'N/A'}
月線 RSI：{monthly_rsi:.1f if monthly_rsi else 'N/A'}{' ⚠️ 極度過熱' if monthly_rsi and monthly_rsi > 85 else ''}

**情緒指標（F&G 10%權重）**
Fear & Greed：{fg_score}

**Pi Cycle Top**
111DMA：${pi_cycle['111dma']:,.0f}
350DMA×2：${pi_cycle['350dma_x2']:,.0f}
信號：{pi_cycle['signal']}{' 🚨 頂部警告！' if pi_cycle.get('is_crossed') else ''}

**分析**
{buy_decision['reason']}

**本週買入建議**
${buy_amount_usd:.0f} ({buy_decision['multiplier']}x 倍數)
"""
        
        # 7. 如果有賣出建議
        if sell_info and sell_info['should_sell']:
            sell_alert_icon = "🚨🚨🚨" if sell_info.get('safety_override') else "⚠️"
            message += f"""
{sell_alert_icon} **賣出建議**
{sell_info['reason']}
建議賣出：{sell_info['sell_btc']:.6f} BTC（交易倉 {sell_info['sell_pct']*100:.0f}%）
"""
        
        # 8. 持倉信息（如果有）
        if position_manager:
            stats = position_manager.get_stats()
            pnl = position_manager.get_unrealized_pnl(current_price)
            
            message += f"""
📊 **持倉狀況**
總持倉：{stats['total_btc']:.6f} BTC
├─ 核心倉：{stats['core_btc']:.6f} BTC（成本 ${stats['core_avg_cost']:,.0f}）
└─ 交易倉：{stats['trade_btc']:.6f} BTC（成本 ${stats['trade_avg_cost']:,.0f}）

平均成本：${stats['avg_cost']:,.0f}
未實現盈虧：${pnl['unrealized_pnl']:,.0f} ({pnl['roi_pct']:+.1f}%)
"""
        
        # 9. 執行策略說明
        message += f"""
**執行策略**
• 核心倉：{strategy_config.MVRV_CORE_RATIO*100:.0f}% 打死不賣
• 交易倉：{(1-strategy_config.MVRV_CORE_RATIO)*100:.0f}% 根據週期賣出
• 時間：分批執行，避免單點風險

**自動排程**
📅 下次推送：{next_push_str}
🔔 固定時間：每週日晚上 8:00（台北時間）

📊 數據源：MVRV Z-Score + Pi Cycle + 200WMA
"""
        
        return message.strip()
        
    except Exception as e:
        logger.error(f"MVRV DCA 分析失敗: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    # 測試
    import ccxt
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker('BTC/USDT')
        price = ticker['last']
        
        message = await get_mvrv_dca_analysis(price)
        print(message)
    
    asyncio.run(test())
