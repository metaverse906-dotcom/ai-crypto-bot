#!/usr/bin/env python3
# scripts/backtests/quick_ada_backtest.py
"""
ADA 山寨幣 DCA 快速回測

基於 BTC Dominance 的動態 DCA 策略
"""

import pandas as pd
import sys
from pathlib import Path

# 添加專案路徑
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.backtests.altcoin_dca_strategy import get_buy_multiplier, get_sell_signal

# 數據路徑
DATA_DIR = Path(__file__).parent / "data"

def load_data():
    """載入所有必要數據"""
    ada_df = pd.read_csv(DATA_DIR / "cardano_price.csv")
    ada_df['date'] = pd.to_datetime(ada_df['date'])
    
    btc_d_df = pd.read_csv(DATA_DIR / "btc_dominance.csv")
    btc_d_df['date'] = pd.to_datetime(btc_d_df['date'])
    
    eth_btc_df = pd.read_csv(DATA_DIR / "eth_btc_ratio.csv")
    eth_btc_df['date'] = pd.to_datetime(eth_btc_df['date'])
    
    # 合併數據
    df = ada_df.merge(btc_d_df, on='date', how='left')
    df = df.merge(eth_btc_df, on='date', how='left')
    
    # 填充缺失值
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    return df

def run_backtest(initial_capital=10000, weekly_investment=100):
    """
    執行回測
    
    Args:
        initial_capital: 初始資金
        weekly_investment: 每週投資額
    """
    print("=" * 70)
    print("ADA 山寨幣 DCA 回測（基於 BTC Dominance）")
    print("=" * 70)
    
    # 載入數據
    print("\n📊 載入數據...")
    df = load_data()
    print(f"✅ 數據範圍: {df['date'].min().date()} ~ {df['date'].max().date()} ({len(df)} 天)")
    
    # 初始化
    cash = initial_capital
    ada_holdings = 0.0
    total_invested = initial_capital
    
    buy_records = []
    sell_records = []
    
    # 每週執行一次（每 7 天）
    print("\n🔄 執行回測...")
    
    for i in range(0, len(df), 7):  # 每週
        row = df.iloc[i]
        date = row['date']
        price = row['price']
        btc_d = row['btc_dominance']
        eth_btc = row['eth_btc_ratio']
        
        # 計算當前持倉價值和利潤
        current_value = ada_holdings * price + cash
        profit_pct = ((current_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0
        
        # 檢查賣出信號
        sell_signal = get_sell_signal(
            btc_dominance=btc_d,
            altseason_index=50.0,  # 使用固定值，因為沒有真實數據
            eth_btc_ratio=eth_btc,
            current_profit_pct=profit_pct
        )
        
        if sell_signal.action != 'HOLD' and ada_holdings > 0:
            # 執行賣出
            sell_amount = ada_holdings * (sell_signal.percentage / 100)
            sell_value = sell_amount * price
            cash += sell_value
            ada_holdings -= sell_amount
            
            sell_records.append({
                'date': date,
                'price': price,
                'ada_sold': sell_amount,
                'usd_received': sell_value,
                'reason': sell_signal.reason
            })
            
            # print(f"{date.date()}: 賣出 {sell_amount:.2f} ADA @ ${price:.4f} - {sell_signal.reason}")
        
        # 買入邏輯
        buy_signal = get_buy_multiplier(btc_d, altseason_index=50.0)
        
        if buy_signal.multiplier > 0:
            # 計算買入金額
            buy_amount_usd = weekly_investment * buy_signal.multiplier
            
            if buy_amount_usd > 0:
                # 執行買入
                ada_bought = buy_amount_usd / price
                ada_holdings += ada_bought
                cash -= buy_amount_usd
                total_invested += buy_amount_usd
                
                buy_records.append({
                    'date': date,
                    'price': price,
                    'usd_spent': buy_amount_usd,
                    'ada_bought': ada_bought,
                    'multiplier': buy_signal.multiplier
                })
                
                # print(f"{date.date()}: 買入 {ada_bought:.2f} ADA @ ${price:.4f} ({buy_signal.multiplier}x)")
    
    # 最終結算
    final_date = df.iloc[-1]['date']
    final_price = df.iloc[-1]['price']
    final_value = ada_holdings * final_price + cash
    total_return = final_value - initial_capital
    return_pct = (total_return / initial_capital) * 100
    
    # HODL 對比
    hodl_ada = initial_capital / df.iloc[0]['price']
    hodl_value = hodl_ada * final_price
    hodl_return_pct = ((hodl_value - initial_capital) / initial_capital) * 100
    
    # 輸出結果
    print("\n" + "=" * 70)
    print("📊 回測結果")
    print("=" * 70)
    
    print(f"\n💰 投資概況:")
    print(f"   初始資金: ${initial_capital:,.2f}")
    print(f"   總投入: ${total_invested:,.2f}")
    print(f"   買入次數: {len(buy_records)} 次")
    print(f"   賣出次數: {len(sell_records)} 次")
    
    print(f"\n📈 績效表現:")
    print(f"   最終價值: ${final_value:,.2f}")
    print(f"   總報酬: ${total_return:,.2f} ({return_pct:+.2f}%)")
    print(f"   ADA 持有: {ada_holdings:.2f} ADA")
    print(f"   現金餘額: ${cash:,.2f}")
    
    print(f"\n🆚 vs HODL:")
    print(f"   HODL 價值: ${hodl_value:,.2f} ({hodl_return_pct:+.2f}%)")
    print(f"   策略超越: {return_pct - hodl_return_pct:+.2f}%")
    
    if len(sell_records) > 0:
        print(f"\n🎯 關鍵賣出事件:")
        for record in sell_records[:5]:  # 顯示前 5 次
            print(f"   {record['date'].date()}: 賣出 ${record['usd_received']:,.0f} - {record['reason']}")
    
    print("\n" + "=" * 70)
    
    return {
        'final_value': final_value,
        'return_pct': return_pct,
        'hodl_return_pct': hodl_return_pct,
        'buy_count': len(buy_records),
        'sell_count': len(sell_records)
    }

if __name__ == "__main__":
    result = run_backtest(
        initial_capital=10000,
        weekly_investment=100
    )
