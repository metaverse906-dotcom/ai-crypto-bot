#!/usr/bin/env python3
"""
組合策略回測：MVRV + F&G + RSI

測試組合指標是否比單一 MVRV 更有效
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import ccxt
from core.position_manager import PositionManager
import logging
import asyncio
import requests

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def download_data():
    """下載歷史數據"""
    print("📥 下載數據中...")
    exchange = ccxt.binance()
    
    ohlcv = exchange.fetch_ohlcv(
        'BTC/USDT',
        timeframe='1w',
        since=int(datetime(2020, 1, 1).timestamp() * 1000),
        limit=1000
    )
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 計算技術指標
    import pandas_ta as ta
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ma_200w'] = df['close'].rolling(window=200, min_periods=50).mean()
    
    # MVRV 代理
    df['price_ratio'] = df['close'] / df['ma_200w']
    def ratio_to_mvrv(ratio):
        if pd.isna(ratio):
            return 1.0
        elif ratio < 1.0:
            return max(0.0, ratio * 1.0)
        elif ratio < 1.5:
            return 1.0 + (ratio - 1.0) * 3.0
        elif ratio < 2.0:
            return 2.5 + (ratio - 1.5) * 3.0
        elif ratio < 3.0:
            return 4.0 + (ratio - 2.0) * 2.5
        else:
            return min(10.0, 6.5 + (ratio - 3.0) * 1.5)
    
    df['mvrv'] = df['price_ratio'].apply(ratio_to_mvrv)
    
    print(f"✅ 數據下載完成：{len(df)} 週")
    return df


def get_fg_score_historical(date):
    """模擬歷史 F&G（實際應該用真實歷史數據，這裡簡化）"""
    # 簡化：用價格動量推估
    # 真實實作應該抓取歷史 F&G API
    return None  # 先不用，避免不準確


class HybridStrategy:
    """組合策略：MVRV + RSI + (可選F&G)"""
    
    def __init__(self, core_ratio=0.4, use_multi_confirm=False):
        self.core_ratio = core_ratio
        self.use_multi_confirm = use_multi_confirm  # 是否需要多重確認
        self.base_weekly = 250
        self.position_manager = PositionManager(core_ratio=core_ratio, data_file=None)
        self.cash = 0
        self.trades = []
        
    def get_buy_signal(self, mvrv, rsi):
        """買入信號"""
        if self.use_multi_confirm:
            # 組合策略：需要雙重確認
            if mvrv < 0.1 and rsi < 30:
                return 3.0, "MVRV+RSI 雙重極度低估"
            elif mvrv < 1.0 and rsi < 40:
                return 1.5, "MVRV+RSI 低估"
            elif mvrv < 1.0 or rsi < 40:
                return 1.0, "單一指標低估"
            elif mvrv < 5.0:
                return 1.0, "正常"
            else:
                return 0.5, "輕度高估"
        else:
            # 純 MVRV 策略
            if mvrv < 0.1:
                return 3.0, "MVRV 極度低估"
            elif mvrv < 1.0:
                return 1.5, "MVRV 低估"
            elif mvrv < 5.0:
                return 1.0, "MVRV 正常"
            elif mvrv < 6.0:
                return 0.5, "MVRV 輕度高估"
            else:
                return 0.0, "MVRV 過熱"
    
    def get_sell_signal(self, mvrv, rsi):
        """賣出信號"""
        if self.use_multi_confirm:
            # 組合策略：需要雙重確認才賣
            if mvrv > 7.0 and rsi > 75:
                return 0.30, "MVRV+RSI 雙重過熱"
            elif mvrv > 8.0 or (mvrv > 6.5 and rsi > 80):
                return 0.20, "強烈過熱"
            elif mvrv > 6.0 and rsi > 70:
                return 0.10, "輕度過熱"
            else:
                return 0.0, "無賣出信號"
        else:
            # 純 MVRV 策略
            if mvrv < 6.0:
                return 0.0, "無"
            elif mvrv < 7.0:
                return 0.10, "MVRV 輕度過熱"
            elif mvrv < 9.0:
                return 0.30, "MVRV 過熱"
            else:
                return 1.0, "MVRV 泡沫"
    
    def execute_week(self, date, price, mvrv, rsi):
        """執行單週"""
        stats_before = self.position_manager.get_stats()
        
        # 買入
        multiplier, buy_reason = self.get_buy_signal(mvrv, rsi)
        if multiplier > 0:
            buy_usd = self.base_weekly * multiplier
            buy_btc = buy_usd / price
            self.position_manager.add_buy(buy_btc, price, buy_reason)
            self.cash -= buy_usd
        
        # 賣出
        sell_pct, sell_reason = self.get_sell_signal(mvrv, rsi)
        if sell_pct > 0 and stats_before['trade_btc'] > 0:
            sell_btc = stats_before['trade_btc'] * sell_pct
            try:
                result = self.position_manager.execute_sell_hifo(sell_btc, price)
                self.cash += result['total_revenue']
            except:
                pass
    
    def run(self, df):
        """執行回測"""
        for idx, row in df.iterrows():
            if pd.notna(row['mvrv']) and pd.notna(row['rsi']):
                self.execute_week(row['date'], row['close'], row['mvrv'], row['rsi'])
        
        stats = self.position_manager.get_stats()
        final_price = df.iloc[-1]['close']
        final_value = stats['total_btc'] * final_price + self.cash
        
        return {
            'final_btc': stats['total_btc'],
            'final_value': final_value,
            'avg_cost': stats['avg_cost']
        }


def main():
    print("\n" + "="*70)
    print(" 組合策略對比測試")
    print("="*70)
    
    df = download_data()
    
    print(f"\n測試期間：{df['date'].min().date()} → {df['date'].max().date()}")
    print(f"週數：{len(df)}")
    
    results = {}
    
    # 1. HODL 基準
    print("\n📊 執行回測...")
    total_btc_hodl = 0
    for idx, row in df.iterrows():
        if pd.notna(row['close']):
            total_btc_hodl += 250 / row['close']
    
    final_price = df.iloc[-1]['close']
    results['HODL'] = {
        'final_btc': total_btc_hodl,
        'final_value': total_btc_hodl * final_price,
        'avg_cost': (250 * len(df)) / total_btc_hodl
    }
    
    # 2. 純 MVRV 策略
    strategy_mvrv = HybridStrategy(core_ratio=0.4, use_multi_confirm=False)
    results['MVRV_Only'] = strategy_mvrv.run(df)
    
    # 3. MVRV + RSI 組合策略
    strategy_hybrid = HybridStrategy(core_ratio=0.4, use_multi_confirm=True)
    results['MVRV+RSI'] = strategy_hybrid.run(df)
    
    # 結果比較
    print("\n" + "="*70)
    print(" 📊 回測結果對比")
    print("="*70)
    
    comparison = pd.DataFrame(results).T
    comparison['btc_vs_hodl'] = ((comparison['final_btc'] / results['HODL']['final_btc']) - 1) * 100
    
    print(f"\n{'策略':<15} {'最終BTC':>12} {'vs HODL':>10} {'平均成本':>12}")
    print("-"*70)
    
    for strategy in ['HODL', 'MVRV_Only', 'MVRV+RSI']:
        r = results[strategy]
        vs_hodl = ((r['final_btc'] / results['HODL']['final_btc']) - 1) * 100
        print(f"{strategy:<15} {r['final_btc']:>12.6f} {vs_hodl:>9.1f}% ${r['avg_cost']:>11,.0f}")
    
    # 結論
    print("\n" + "="*70)
    print(" 💡 結論")
    print("="*70)
    
    mvrv_improvement = ((results['MVRV_Only']['final_btc'] / results['HODL']['final_btc']) - 1) * 100
    hybrid_improvement = ((results['MVRV+RSI']['final_btc'] / results['HODL']['final_btc']) - 1) * 100
    
    print(f"\n純 MVRV：      比 HODL 多 {mvrv_improvement:+.1f}%")
    print(f"MVRV+RSI 組合：比 HODL 多 {hybrid_improvement:+.1f}%")
    
    if hybrid_improvement > mvrv_improvement:
        delta = hybrid_improvement - mvrv_improvement
        print(f"\n✅ 組合策略更優！多 {delta:.1f}% BTC")
    else:
        delta = mvrv_improvement - hybrid_improvement
        print(f"\n⚠️ 純 MVRV 更優！組合策略反而少 {delta:.1f}% BTC")
        print(f"\n可能原因：")
        print(f"- 雙重確認導致買入時機延遲")
        print(f"- 雙重確認導致賣出時機延遲")
        print(f"- RSI 在長期趨勢中產生誤導信號")


if __name__ == '__main__':
    main()
