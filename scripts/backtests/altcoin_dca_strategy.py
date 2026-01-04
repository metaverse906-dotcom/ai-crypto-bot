#!/usr/bin/env python3
# scripts/backtests/altcoin_dca_strategy.py
"""
山寨幣 DCA 策略邏輯

基於 BTC Dominance 和 Altcoin Season Index 的動態 DCA 策略
"""

from typing import Dict, Literal
from dataclasses import dataclass


@dataclass
class BuySignal:
    """買入信號"""
    multiplier: float  # 買入倍數
    reason: str  # 原因
    confidence: Literal['high', 'medium', 'low']


@dataclass
class SellSignal:
    """賣出信號"""
    action: Literal['HOLD', 'SELL_PRINCIPAL', 'SELL_50', 'SELL_ALL']
    percentage: float  # 賣出百分比
    reason: str
    urgency: Literal['low', 'medium', 'high', 'critical']


def get_buy_multiplier(btc_dominance: float, altseason_index: float = None) -> BuySignal:
    """
    決定買入倍數
    
    Args:
        btc_dominance: BTC 主導指數 (0-100)
        altseason_index: 山寨幣季節指數 (0-100), 可選
    
    Returns:
        BuySignal: 包含倍數、原因和信心度
    """
    # 優先檢查: Altseason Index
    if altseason_index and altseason_index > 75:
        return BuySignal(
            multiplier=0.0,
            reason=f'Altseason Index {altseason_index:.0f} > 75，山寨幣過熱',
            confidence='high'
        )
    
    # 基於 BTC Dominance 的買入邏輯
    if btc_dominance > 65:
        return BuySignal(
            multiplier=3.0,
            reason=f'BTC.D {btc_dominance:.1f}% 超高，山寨幣超便宜',
            confidence='high'
        )
    elif btc_dominance > 60:
        return BuySignal(
            multiplier=2.5,
            reason=f'BTC.D {btc_dominance:.1f}% 很高，山寨幣便宜',
            confidence='high'
        )
    elif btc_dominance > 55:
        return BuySignal(
            multiplier=2.0,
            reason=f'BTC.D {btc_dominance:.1f}% 較高，適合買入',
            confidence='medium'
        )
    elif btc_dominance > 50:
        return BuySignal(
            multiplier=1.5,
            reason=f'BTC.D {btc_dominance:.1f}% 中等偏高',
            confidence='medium'
        )
    elif btc_dominance > 45:
        return BuySignal(
            multiplier=1.0,
            reason=f'BTC.D {btc_dominance:.1f}% 正常區間',
            confidence='low'
        )
    elif btc_dominance > 40:
        return BuySignal(
            multiplier=0.5,
            reason=f'BTC.D {btc_dominance:.1f}% 偏低，減速買入',
            confidence='low'
        )
    else:
        return BuySignal(
            multiplier=0.0,
            reason=f'BTC.D {btc_dominance:.1f}% < 40%，準備賣出',
            confidence='high'
        )


def detect_btc_dominance_bottom(btc_d_history: list[float], current_btc_d: float) -> bool:
    """
    檢測 BTC Dominance 是否觸底反彈
    
    定義: 過去 7 天最低點，且今天開始上升
    
    Args:
        btc_d_history: 過去 14 天的 BTC.D 數據
        current_btc_d: 當前 BTC.D
    
    Returns:
        bool: 是否觸底反彈
    """
    if len(btc_d_history) < 14:
        return False
    
    # 過去 7 天的最低點
    recent_7d = btc_d_history[-7:]
    min_7d = min(recent_7d)
    
    # 過去 14 天的平均值
    avg_14d = sum(btc_d_history) / len(btc_d_history)
    
    # 觸底反彈條件:
    # 1. 當前是過去 7 天最低的 (±0.5%)
    # 2. 且低於 14 天平均
    # 3. 且今天開始上升
    is_at_bottom = abs(current_btc_d - min_7d) < 0.5
    below_average = current_btc_d < avg_14d
    starting_to_rise = current_btc_d > btc_d_history[-1]  # 比昨天高
    
    return is_at_bottom and below_average and starting_to_rise


def get_sell_signal(
    btc_dominance: float,
    altseason_index: float,
    eth_btc_ratio: float,
    current_profit_pct: float,
    btc_d_history: list[float] = None
) -> SellSignal:
    """
    決定賣出策略
    
    Args:
        btc_dominance: 當前 BTC.D
        altseason_index: 當前 Altseason Index
        eth_btc_ratio: 當前 ETH/BTC 比率
        current_profit_pct: 當前持倉利潤百分比
        btc_d_history: BTC.D 歷史數據（用於檢測觸底）
    
    Returns:
        SellSignal: 賣出信號
    """
    # 優先級 1: Altseason Index > 75 (最高優先級)
    if altseason_index > 75:
        return SellSignal(
            action='SELL_ALL',
            percentage=100.0,
            reason=f'Altseason Index {altseason_index:.0f} 超過 75，歷史頂部信號',
            urgency='critical'
        )
    
    # 優先級 2: BTC.D 觸底反彈 (極度危險)
    if btc_d_history and detect_btc_dominance_bottom(btc_d_history, btc_dominance):
        return SellSignal(
            action='SELL_ALL',
            percentage=100.0,
            reason='BTC.D 觸底反彈，山寨幣即將崩盤',
            urgency='critical'
        )
    
    # 優先級 3: ETH/BTC 在歷史高位
    if eth_btc_ratio > 0.08:
        return SellSignal(
            action='SELL_50',
            percentage=50.0,
            reason=f'ETH/BTC {eth_btc_ratio:.4f} 在高位，部分獲利了結',
            urgency='high'
        )
    
    # 優先級 4: 零成本持倉策略（翻倍）
    if current_profit_pct >= 100:
        return SellSignal(
            action='SELL_PRINCIPAL',
            percentage=50.0,  # 賣掉本金，留下利潤
            reason=f'已翻倍（+{current_profit_pct:.0f}%），零成本持倉',
            urgency='medium'
        )
    
    # 優先級 5: Altseason Index 接近危險區
    if altseason_index > 65:
        return SellSignal(
            action='SELL_50',
            percentage=50.0,
            reason=f'Altseason Index {altseason_index:.0f} 接近 75，提前獲利',
            urgency='medium'
        )
    
    # 沒有賣出信號
    return SellSignal(
        action='HOLD',
        percentage=0.0,
        reason='繼續持有',
        urgency='low'
    )


def calculate_stop_loss(entry_price: float, current_price: float, stop_loss_pct: float = -50.0) -> bool:
    """
    檢查是否觸發止損
    
    Args:
        entry_price: 平均買入價
        current_price: 當前價格
        stop_loss_pct: 止損百分比（默認 -50%）
    
    Returns:
        bool: 是否應該止損
    """
    loss_pct = ((current_price - entry_price) / entry_price) * 100
    return loss_pct <= stop_loss_pct


# 測試函數
if __name__ == "__main__":
    # 測試買入邏輯
    print("=== 買入邏輯測試 ===")
    
    test_cases = [
        (70, 30),   # BTC.D 很高
        (50, 50),   # 正常
        (35, 80),   # BTC.D 低 + Altseason
    ]
    
    for btc_d, alt_idx in test_cases:
        signal = get_buy_multiplier(btc_d, alt_idx)
        print(f"BTC.D {btc_d}%, Altseason {alt_idx}: {signal.multiplier}x - {signal.reason}")
    
    print("\n=== 賣出邏輯測試 ===")
    
    # 測試 Altseason 賣出
    signal = get_sell_signal(45, 80, 0.06, 50)
    print(f"Altseason 80: {signal.action} - {signal.reason}")
    
    # 測試翻倍賣出
    signal = get_sell_signal(50, 50, 0.06, 120)
    print(f"利潤 120%: {signal.action} - {signal.reason}")
    
    # 測試 ETH/BTC 高位
    signal = get_sell_signal(50, 50, 0.085, 50)
    print(f"ETH/BTC 0.085: {signal.action} - {signal.reason}")
