#!/usr/bin/env python3
"""
MVRV-Based Dynamic DCA 策略回測

目標：驗證「文檔策略」是否真的比 HODL 更有效
- 基於 MVRV Z-Score 的動態買入/賣出
- HIFO 倉位管理
- 核心倉/交易倉分割
- 測試不同保留比例（30%, 40%, 50%）

回測期間：2020-2024（包含完整牛熊週期）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from core.position_manager import PositionManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_historical_data(start_date='2020-01-01', end_date='2024-12-31'):
    """
    下載歷史週線數據
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        DataFrame: OHLCV 數據
    """
    print(f"\n📥 下載歷史數據 ({start_date} → {end_date})...")
    
    exchange = ccxt.binance()
    
    start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
    
    all_ohlcv = []
    current_ts = start_ts
    
    while current_ts < end_ts:
        ohlcv = exchange.fetch_ohlcv(
            'BTC/USDT',
            timeframe='1w',
            since=current_ts,
            limit=500
        )
        
        if not ohlcv:
            break
            
        all_ohlcv.extend(ohlcv)
        current_ts = ohlcv[-1][0] + 1
        print(f"  已下載 {len(all_ohlcv)} 週...")
    
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    print(f"✅ 下載完成：{len(df)} 週的數據")
    return df


def calculate_mvrv_proxy(df):
    """
    計算 MVRV 代理指標（因為沒有真實鏈上數據）
    
    使用價格相對 200週均線作為 MVRV 的近似值
    這不是真正的 MVRV，但相關性很高
    
    映射關係（基於歷史觀察）：
    - Price @ 200WMA → MVRV ≈ 1.0
    - Price = 2x 200WMA → MVRV ≈ 3.5
    - Price = 3x 200WMA → MVRV ≈ 6.0
    - Price = 4x+ 200WMA → MVRV ≈ 8.0+
    """
    df['ma_200w'] = df['close'].rolling(window=200, min_periods=50).mean()
    df['price_ratio'] = df['close'] / df['ma_200w']
    
    # 非線性映射（越高倍數，MVRV 增長越快）
    def ratio_to_mvrv(ratio):
        if pd.isna(ratio):
            return 1.0
        elif ratio < 1.0:
            return max(0.0, ratio * 1.0)  # 低於均線時線性
        elif ratio < 1.5:
            return 1.0 + (ratio - 1.0) * 3.0  # 1.5x → MVRV 2.5
        elif ratio < 2.0:
            return 2.5 + (ratio - 1.5) * 3.0  # 2.0x → MVRV 4.0
        elif ratio < 3.0:
            return 4.0 + (ratio - 2.0) * 2.5  # 3.0x → MVRV 6.5
        else:
            return min(10.0, 6.5 + (ratio - 3.0) * 1.5)  # 限制最高 10
    
    df['mvrv_proxy'] = df['price_ratio'].apply(ratio_to_mvrv)
    
    return df


class MVRVStrategy:
    """
    MVRV 動態 DCA 策略
    
    根據文檔中的策略矩陣執行買賣決策
    """
    
    def __init__(self, 
                 core_ratio=0.4,
                 base_weekly_usd=250,
                 initial_cash=0):
        """
        初始化策略
        
        Args:
            core_ratio: 核心倉比例（0.3 = 30%, 0.4 = 40%, 0.5 = 50%）
            base_weekly_usd: 基礎每週投入金額
            initial_cash: 初始現金（用於測試）
        """
        self.core_ratio = core_ratio
        self.base_weekly = base_weekly_usd
        self.cash = initial_cash
        self.position_manager = PositionManager(core_ratio=core_ratio, data_file=None)
        
        # 交易記錄
        self.trades = []
        self.weekly_log = []
    
    def get_buy_multiplier(self, mvrv):
        """
        根據 MVRV 決定買入倍數（文檔策略）
        
        MVRV Z-Score 買入矩陣：
        < 0.1  → 3.0x (極度低估)
        0.1-1.0 → 1.5x (積累區)
        1.0-5.0 → 1.0x (正常)
        5.0-6.0 → 0.5x (減速)
        >= 6.0 → 0x (停止)
        """
        if mvrv < 0.1:
            return 3.0
        elif mvrv < 1.0:
            return 1.5
        elif mvrv < 5.0:
            return 1.0
        elif mvrv < 6.0:
            return 0.5
        else:
            return 0.0  # 停止買入
    
    def get_sell_percentage(self, mvrv):
        """
        根據 MVRV 決定賣出比例（相對交易倉）
        
        MVRV Z-Score 賣出矩陣：
        6.0-7.0 → 10% 交易倉
        7.0-8.0 → 30% 交易倉
        8.0-9.0 → 50% 交易倉
        >= 9.0 → 100% 交易倉
        """
        if mvrv < 6.0:
            return 0.0
        elif mvrv < 7.0:
            return 0.10
        elif mvrv < 8.0:
            return 0.30
        elif mvrv < 9.0:
            return 0.50
        else:
            return 1.0  # 清空交易倉
    
    def execute_week(self, date, price, mvrv):
        """
        執行單週策略
        
        Args:
            date: 日期
            price: 當週價格
            mvrv: MVRV 值
        """
        stats_before = self.position_manager.get_stats()
        
        action = "HOLD"
        details = ""
        
        # 1. 決定是否買入
        buy_multiplier = self.get_buy_multiplier(mvrv)
        if buy_multiplier > 0:
            buy_amount_usd = self.base_weekly * buy_multiplier
            buy_amount_btc = buy_amount_usd / price
            
            self.position_manager.add_buy(
                amount=buy_amount_btc,
                price=price,
                note=f"MVRV={mvrv:.2f}"
            )
            
            self.cash -= buy_amount_usd
            action = "BUY"
            details = f"{buy_amount_btc:.6f} BTC @ ${price:,.0f} (${buy_amount_usd:.0f}, {buy_multiplier}x)"
            
            self.trades.append({
                'date': date,
                'action': 'BUY',
                'price': price,
                'amount': buy_amount_btc,
                'usd_value': buy_amount_usd,
                'mvrv': mvrv
            })
        
        # 2. 決定是否賣出（只有交易倉可賣）
        sell_pct = self.get_sell_percentage(mvrv)
        if sell_pct > 0:
            trade_btc = stats_before['trade_btc']
            if trade_btc > 0:
                sell_amount = trade_btc * sell_pct
                
                try:
                    result = self.position_manager.execute_sell_hifo(
                        amount=sell_amount,
                        current_price=price
                    )
                    
                    self.cash += result['total_revenue']
                    action = "SELL" if buy_multiplier == 0 else "BUY+SELL"
                    details += f" | 賣出 {sell_amount:.6f} BTC → ${result['total_revenue']:,.0f} (獲利 ${result['total_profit']:,.0f})"
                    
                    self.trades.append({
                        'date': date,
                        'action': 'SELL',
                        'price': price,
                        'amount': sell_amount,
                        'usd_value': result['total_revenue'],
                        'mvrv': mvrv,
                        'profit': result['total_profit']
                    })
                    
                except ValueError as e:
                    logger.warning(f"賣出失敗: {e}")
        
        # 記錄狀態
        stats_after = self.position_manager.get_stats()
        pnl = self.position_manager.get_unrealized_pnl(price)
        
        self.weekly_log.append({
            'date': date,
            'price': price,
            'mvrv': mvrv,
            'action': action,
            'details': details,
            'total_btc': stats_after['total_btc'],
            'cash': self.cash,
            'portfolio_value': pnl['current_value'] + self.cash,
            'unrealized_pnl': pnl['unrealized_pnl']
        })
    
    def run_backtest(self, df):
        """
        執行完整回測
        
        Args:
            df: 包含 OHLCV 和 MVRV 的 DataFrame
        """
        print(f"\n🚀 開始回測：核心倉 {self.core_ratio*100:.0f}% 策略")
        print(f"   基礎週投入：${self.base_weekly}")
        print("=" * 70)
        
        for idx, row in df.iterrows():
            self.execute_week(
                date=row['date'],
                price=row['close'],
                mvrv=row['mvrv_proxy']
            )
        
        # 計算最終績效
        final_stats = self.position_manager.get_stats()
        final_price = df.iloc[-1]['close']
        final_pnl = self.position_manager.get_unrealized_pnl(final_price)
        
        total_invested = final_stats['total_invested']
        final_portfolio_value = final_pnl['current_value'] + self.cash
        
        print(f"\n📊 回測結果")
        print("=" * 70)
        print(f"最終 BTC 持倉：{final_stats['total_btc']:.6f} BTC")
        print(f"  ├─ 核心倉：{final_stats['core_btc']:.6f} BTC (成本 ${final_stats['core_avg_cost']:,.0f})")
        print(f"  └─ 交易倉：{final_stats['trade_btc']:.6f} BTC (成本 ${final_stats['trade_avg_cost']:,.0f})")
        print(f"\n剩餘現金：${self.cash:,.2f}")
        print(f"總投入：${total_invested:,.2f}")
        print(f"組合總值：${final_portfolio_value:,.2f}")
        print(f"報酬率：{final_pnl['roi_pct']:+.2f}%")
        print(f"平均成本：${final_stats['avg_cost']:,.2f}")
        
        return {
            'final_btc': final_stats['total_btc'],
            'final_cash': self.cash,
            'total_invested': total_invested,
            'final_value': final_portfolio_value,
            'roi_pct': final_pnl['roi_pct'],
            'avg_cost': final_stats['avg_cost'],
            'core_avg_cost': final_stats['core_avg_cost'],
            'num_buys': len([t for t in self.trades if t['action'] == 'BUY']),
            'num_sells': len([t for t in self.trades if t['action'] == 'SELL'])
        }


def simple_hodl_backtest(df, weekly_usd=250):
    """
    簡單 HODL 回測（對照組）
    
    每週固定買入，永不賣出
    """
    print(f"\n🏦 HODL 策略回測")
    print("=" * 70)
    
    total_btc = 0
    total_invested = 0
    
    for idx, row in df.iterrows():
        buy_amount_usd = weekly_usd
        buy_amount_btc = buy_amount_usd / row['close']
        
        total_btc += buy_amount_btc
        total_invested += buy_amount_usd
    
    final_price = df.iloc[-1]['close']
    final_value = total_btc * final_price
    roi_pct = ((final_value - total_invested) / total_invested) * 100
    avg_cost = total_invested / total_btc
    
    print(f"最終 BTC：{total_btc:.6f} BTC")
    print(f"總投入：${total_invested:,.2f}")
    print(f"最終市值：${final_value:,.2f}")
    print(f"報酬率：{roi_pct:+.2f}%")
    print(f"平均成本：${avg_cost:,.2f}")
    
    return {
        'final_btc': total_btc,
        'total_invested': total_invested,
        'final_value': final_value,
        'roi_pct': roi_pct,
        'avg_cost': avg_cost
    }


def main():
    """主程序：比較不同策略"""
    
    print("\n" + "=" * 70)
    print(" MVRV-Based Dynamic DCA 策略回測")
    print(" 目標：驗證文檔策略是否優於 HODL")
    print("=" * 70)
    
    # 1. 下載數據
    df = download_historical_data(start_date='2020-01-01', end_date='2024-12-31')
    
    # 2. 計算 MVRV 代理指標
    df = calculate_mvrv_proxy(df)
    
    print(f"\n📈 數據統計：")
    print(f"   期間：{df['date'].min().date()} → {df['date'].max().date()}")
    print(f"   週數：{len(df)} 週")
    print(f"   價格範圍：${df['close'].min():,.0f} - ${df['close'].max():,.0f}")
    print(f"   MVRV 範圍：{df['mvrv_proxy'].min():.2f} - {df['mvrv_proxy'].max():.2f}")
    
    # 3. 執行回測
    results = {}
    
    # HODL 基準
    results['HODL'] = simple_hodl_backtest(df, weekly_usd=250)
    
    # MVRV 策略（不同核心倉比例）
    for core_ratio in [0.3, 0.4, 0.5]:
        strategy = MVRVStrategy(core_ratio=core_ratio, base_weekly_usd=250)
        result = strategy.run_backtest(df)
        results[f'MVRV_{int(core_ratio*100)}%'] = result
    
    # 4. 比較結果
    print("\n\n" + "=" * 70)
    print(" 🏆 策略比較")
    print("=" * 70)
    
    comparison = pd.DataFrame(results).T
    comparison['btc_vs_hodl'] = (comparison['final_btc'] / results['HODL']['final_btc'] - 1) * 100
    
    print(comparison[['final_btc', 'roi_pct', 'avg_cost', 'btc_vs_hodl']].to_string())
    
    # 5. 結論
    print("\n\n" + "=" * 70)
    print(" 💡 結論")
    print("=" * 70)
    
    best_strategy = comparison['final_btc'].idxmax()
    best_btc = comparison.loc[best_strategy, 'final_btc']
    hodl_btc = results['HODL']['final_btc']
    improvement = ((best_btc / hodl_btc) - 1) * 100
    
    print(f"最佳策略：{best_strategy}")
    print(f"最終 BTC：{best_btc:.6f} BTC")
    print(f"相比 HODL：+{improvement:.2f}% 更多的 BTC")
    print(f"\n✅ 策略{'有效' if improvement > 0 else '無效'}！")
    
    # 儲存結果
    output_file = "data/backtest/mvrv_strategy_results.csv"
    os.makedirs("data/backtest", exist_ok=True)
    comparison.to_csv(output_file)
    print(f"\n📁 結果已保存：{output_file}")


if __name__ == '__main__':
    main()
