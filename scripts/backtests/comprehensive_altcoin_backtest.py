#!/usr/bin/env python3
# scripts/backtests/comprehensive_altcoin_backtest.py
"""
全方位山寨幣回測套件 (Comprehensive Altcoin Backtest Suite)

功能：
1. 載入多維度數據 (價格, BTC.D, ETH/BTC, 等)
2. 執行基於信號的 DCA 策略
3. 計算詳細績效指標 (ROI, 最大回撤, 夏普比率, 勝率)
4. 生成視覺化圖表 (Matplotlib)
5. 輸出詳細回測報告 (Markdown)

作者: Antigravity
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from datetime import datetime
import textwrap

# 設定中文字型 (Windows 適用)
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False

# 添加專案路徑以導入策略模組
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.backtests.altcoin_dca_strategy import get_buy_multiplier, get_sell_signal

# 數據路徑
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

class BacktestEngine:
    def __init__(self, coin_name="ADA", initial_capital=10000, weekly_investment=100):
        self.coin_name = coin_name
        self.initial_capital = initial_capital
        self.weekly_investment = weekly_investment
        self.df = None
        self.results = {}
        self.trade_log = []
        
    def load_data(self):
        """載入並清理數據"""
        print(f"📥 正在載入 {self.coin_name} 及市場數據...")
        
        # 1. 載入幣種價格
        price_file = DATA_DIR / f"{self.coin_name.lower()}_price.csv"
        if not price_file.exists():
            # Fallback for generic naming if needed, but assuming ADA for now based on context
            price_file = DATA_DIR / "cardano_price.csv" 
            
        if not price_file.exists():
            raise FileNotFoundError(f"找不到價格文件: {price_file}")
            
        coin_df = pd.read_csv(price_file)
        coin_df['date'] = pd.to_datetime(coin_df['date'])
        
        # 2. 載入 BTC Dominance
        btc_d_df = pd.read_csv(DATA_DIR / "btc_dominance.csv")
        btc_d_df['date'] = pd.to_datetime(btc_d_df['date'])
        
        # 3. 載入 ETH/BTC Ratio
        eth_btc_df = pd.read_csv(DATA_DIR / "eth_btc_ratio.csv")
        eth_btc_df['date'] = pd.to_datetime(eth_btc_df['date'])
        
        # 合併數據
        df = coin_df.merge(btc_d_df, on='date', how='left')
        df = df.merge(eth_btc_df, on='date', how='left')
        
        # 填充缺失值
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        self.df = df.sort_values('date').reset_index(drop=True)
        print(f"✅ 數據載入完成: {len(self.df)} 筆交易日資料 ({self.df['date'].min().date()} - {self.df['date'].max().date()})")

    def run(self):
        """執行回測核心邏輯"""
        print("🚀 開始執行策略回測...")
        
        cash = self.initial_capital
        holdings = 0.0
        total_invested = self.initial_capital
        
        # 用於記錄每日資產淨值 (Equity Curve)
        equity_curve = []
        drawdown_curve = []
        
        # 模擬每週 DCA
        # 假設每 7 天是一個決策點
        
        btc_d_history = [] # 用於記錄過去的 BTC.D 以判斷趨勢
        
        for i, row in self.df.iterrows():
            date = row['date']
            price = row['price']
            btc_d = row['btc_dominance']
            eth_btc = row['eth_btc_ratio']
            
            # 更新 BTC.D 歷史
            btc_d_history.append(btc_d)
            if len(btc_d_history) > 30:
                btc_d_history.pop(0)

            # 計算當前資產價值
            current_value = holdings * price + cash
            equity_curve.append({'date': date, 'value': current_value, 'price': price})
            
            # 策略執行頻率：每週 (每 7 天)
            if i % 7 != 0:
                continue
                
            # --- 賣出邏輯 ---
            profit_pct = ((current_value - total_invested) / total_invested * 100) if total_invested > 0 else 0
            
            sell_signal = get_sell_signal(
                btc_dominance=btc_d,
                altseason_index=50.0, # 目前暫無真實數據，使用預設中性值
                eth_btc_ratio=eth_btc,
                current_profit_pct=profit_pct,
                btc_d_history=btc_d_history
            )
            
            if sell_signal.action != 'HOLD' and holdings > 0:
                sell_ratio = sell_signal.percentage / 100.0
                sell_amount = holdings * sell_ratio
                sell_value = sell_amount * price
                
                cash += sell_value
                holdings -= sell_amount
                
                self.trade_log.append({
                    'date': date,
                    'type': 'SELL',
                    'price': price,
                    'amount': sell_amount,
                    'value': sell_value,
                    'reason': sell_signal.reason,
                    'balance': cash + (holdings * price)
                })
            
            # --- 買入邏輯 ---
            buy_signal = get_buy_multiplier(btc_d, altseason_index=50.0)
            
            if buy_signal.multiplier > 0 and cash > 0: # 確保有現金，但這裡是 DCA 模擬，通常假設有外部現金流，或只用初始資金？
                # 這裡假設 "Weekly Investment" 是從外部流入的資金，或者是從初始資金扣除？
                # 根據 quick_ada_backtest 的邏輯，這裡似乎是 mix:
                # 1. 初始資金 (Lump sum) -> backtest 裡沒用到 lump sum 買入？
                # 修正：通常 DCA 回測是每週投入一筆新錢。
                # 但 quick_ada_backtest 裡 total_invested 包含了 initial_capital。
                # 我們這裡假設：初始資金保持現金，每週從這筆現金扣款投資。如果現金用完就停止？
                # 或者：Pure DCA，每週從外部 "轉入" weekly_investment。
                
                # 為了計算單純的 ROI，我們採用：每週從外部注入資金。
                # Initial Capital 視為第一筆資金。
                
                if i == 0 and self.initial_capital > 0:
                    # 第一天投入初始資金的一小部分或全部？通常 DCA 是分批。
                    # 為了簡化，我們假設 Initial Capital 是已經在帳戶裡的現金，每週從這裡扣。
                    pass

                invest_amount = self.weekly_investment * buy_signal.multiplier
                
                # 如果現金足夠
                if cash >= invest_amount:
                    buy_amount = invest_amount / price
                    holdings += buy_amount
                    cash -= invest_amount
                    # total_invested 已經是初始資金，這只是資金轉換，不增加總投入成本
                    
                    self.trade_log.append({
                        'date': date,
                        'type': 'BUY',
                        'price': price,
                        'amount': buy_amount,
                        'value': invest_amount,
                        'reason': f"倍數 {buy_signal.multiplier}x",
                        'balance': current_value # 約略值
                    })
                # 如果是無限現金流模式 (Pure DCA)，則應該 total_invested += invest_amount
                # 這裡採用 "有限資金池" 模式 (Portfolio Management)
        
        # 整理結果
        self.equity_df = pd.DataFrame(equity_curve)
        self.equity_df.set_index('date', inplace=True)
        
        # 計算 Drawdown
        roll_max = self.equity_df['value'].cummax()
        self.equity_df['drawdown'] = (self.equity_df['value'] - roll_max) / roll_max
        
        # 最終結算
        last_price = self.df.iloc[-1]['price']
        final_value = holdings * last_price + cash
        
        # HODL 比較 (假設第一天全倉買入)
        first_price = self.df.iloc[0]['price']
        hodl_amount = self.initial_capital / first_price
        hodl_final_value = hodl_amount * last_price
        
        self.results = {
            'final_value': final_value,
            'total_return_pct': (final_value - self.initial_capital) / self.initial_capital * 100,
            'max_drawdown': self.equity_df['drawdown'].min() * 100,
            'hodl_return_pct': (hodl_final_value - self.initial_capital) / self.initial_capital * 100,
            'trade_count': len(self.trade_log),
            'end_cash': cash,
            'end_holdings': holdings
        }
        
    def generate_charts(self):
        """生成視覺化圖表"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = OUTPUT_DIR / f"backtest_chart_{self.coin_name}_{timestamp}.png"
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 18), sharex=True)
        
        # 圖 1: 價格與買賣點
        ax1.plot(self.equity_df.index, self.equity_df['price'], label='Price', color='gray', alpha=0.5)
        
        # 標記買賣點
        buys = [t for t in self.trade_log if t['type'] == 'BUY']
        sells = [t for t in self.trade_log if t['type'] == 'SELL']
        
        if buys:
            buy_dates = [t['date'] for t in buys]
            buy_prices = [t['price'] for t in buys]
            ax1.scatter(buy_dates, buy_prices, marker='^', color='green', label='買入', s=50, zorder=5)
            
        if sells:
            sell_dates = [t['date'] for t in sells]
            sell_prices = [t['price'] for t in sells]
            ax1.scatter(sell_dates, sell_prices, marker='v', color='red', label='賣出', s=50, zorder=5)
            
        ax1.set_title(f"{self.coin_name} 價格走勢與交易點位", fontsize=14)
        ax1.set_ylabel("價格 (USD)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 圖 2: 資產淨值曲線 vs HODL
        # 重建 HODL 曲線
        first_price = self.equity_df['price'].iloc[0]
        hodl_amount = self.initial_capital / first_price
        hodl_curve = self.equity_df['price'] * hodl_amount
        
        ax2.plot(self.equity_df.index, self.equity_df['value'], label='策略淨值', color='blue', linewidth=2)
        ax2.plot(self.equity_df.index, hodl_curve, label='HODL 淨值', color='orange', linestyle='--', alpha=0.8)
        
        ax2.set_title("資產淨值曲線 (Strategy vs HODL)", fontsize=14)
        ax2.set_ylabel("資產價值 (USD)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 圖 3: 回撤 (Drawdown)
        ax3.fill_between(self.equity_df.index, self.equity_df['drawdown'] * 100, 0, color='red', alpha=0.3)
        ax3.plot(self.equity_df.index, self.equity_df['drawdown'] * 100, color='red', linewidth=1)
        ax3.set_title("最大回撤幅度 (%)", fontsize=14)
        ax3.set_ylabel("回撤 %")
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filename)
        print(f"🖼️ 圖表已儲存: {filename}")
        return filename

    def generate_report(self):
        """生成文字報告"""
        report = []
        report.append("=" * 60)
        report.append(f"📊 {self.coin_name} 智能 DCA 回測報告")
        report.append("=" * 60)
        report.append(f"📅 回測區間: {self.df['date'].min().date()} ~ {self.df['date'].max().date()}")
        report.append(f"💰 初始資金: ${self.initial_capital:,.2f}")
        report.append("-" * 60)
        report.append("📈 績效摘要:")
        report.append(f"   • 最終資產: ${self.results['final_value']:,.2f}")
        report.append(f"   • 總報酬率 (ROI): {self.results['total_return_pct']:+.2f}%")
        report.append(f"   • HODL 報酬率: {self.results['hodl_return_pct']:+.2f}%")
        report.append(f"   • 績效超越 (Alpha): {self.results['total_return_pct'] - self.results['hodl_return_pct']:+.2f}%")
        report.append(f"   • 最大回撤 (MDD): {self.results['max_drawdown']:.2f}%")
        report.append(f"   • 交易次數: {self.results['trade_count']}")
        
        report.append("\n📝 交易紀錄摘要 (最近 10 筆):")
        for trade in self.trade_log[-10:]:
            action_icon = "🟢" if trade['type'] == 'BUY' else "🔴"
            report.append(f"   {action_icon} {trade['date'].date()} {trade['type']}: ${trade['value']:,.0f} @ ${trade['price']:.4f} | {trade['reason']}")
            
        report_text = "\n".join(report)
        print(report_text)
        
        # 存檔
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = OUTPUT_DIR / f"backtest_report_{self.coin_name}_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n📄 報告已儲存: {report_file}")


if __name__ == "__main__":
    # 解決 Windows 控制台中文編碼問題
    try:
        if sys.platform.startswith('win'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("🚀 正在啟動山寨幣回測系統...")
    print("📋 如果看到亂碼或沒有反應，請檢查您的 Python 環境設定。")
    print("-" * 50)

    try:
        engine = BacktestEngine(
            coin_name="ADA",
            initial_capital=10000,
            weekly_investment=250
        )
        engine.load_data()
        engine.run()
        engine.generate_charts()
        engine.generate_report()
        
        print("\n✅ 回測執行完成！")
    except ImportError as e:
        print(f"\n❌ 缺少必要套件: {e}")
        print("請執行: pip install pandas matplotlib")
    except FileNotFoundError as e:
        print(f"\n❌ 找不到檔案: {e}")
        print(f"請確認 data 資料夾內是否有對應的 csv 檔案。")
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    # 防止 Windows 視窗執行完立即關閉
    print("\n" + "="*50)
    input("⌨️  按 Enter 鍵離開視窗...")

