#!/usr/bin/env python3
# tools/statistical_backtest.py
"""
統計抽樣回測系統
- 從幣安 API 抓取數據
- 隨機時間區間抽樣
- 95% 信賴區間計算
- 考慮策略特性（時間框架、時段限制）
"""

import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import random
import time
from scipy import stats

class StatisticalBacktester:
    def __init__(self, symbol='BTC/USDT'):
        self.symbol = symbol
        self.exchange = ccxt.binance()
        self.initial_capital = 1000.0
    
    # ==================== 數據抓取 ====================
    
    def fetch_data(self, timeframe, start_date, end_date):
        """
        從幣安抓取歷史數據
        
        Args:
            timeframe: '15m' or '4h'
            start_date: '2023-01-01'
            end_date: '2023-12-31'
        """
        print(f"  正在抓取 {timeframe} 數據: {start_date} - {end_date}")
        
        since = self.exchange.parse8601(f"{start_date}T00:00:00Z")
        until = self.exchange.parse8601(f"{end_date}T23:59:59Z")
        
        all_data = []
        current = since
        
        while current < until:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    self.symbol, 
                    timeframe,
                    since=current,
                    limit=1000
                )
                
                if not ohlcv:
                    break
                
                all_data.extend(ohlcv)
                current = ohlcv[-1][0] + 1
                
                # API 限制：避免過快請求
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    錯誤: {e}，重試...")
                time.sleep(2)
                continue
        
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"  抓取完成: {len(df)} 根 K 線")
        return df
    
    # ==================== 抽樣策略 ====================
    
    def generate_sample_periods(self, total_start, total_end, n_samples=20, period_months=3):
        """
        生成隨機不重疊時間區間
        
        Args:
            total_start: '2020-01-01'
            total_end: '2024-12-31'
            n_samples: 抽樣數量
            period_months: 每個區間月數
        """
        start = pd.to_datetime(total_start)
        end = pd.to_datetime(total_end)
        
        total_days = (end - start).days
        period_days = period_months * 30
        
        # 生成所有可能的起始點
        possible_starts = list(range(0, total_days - period_days, period_days))
        
        # 隨機選擇 n 個不重疊區間
        selected = random.sample(possible_starts, min(n_samples, len(possible_starts)))
        
        samples = []
        for offset in sorted(selected):
            sample_start = start + timedelta(days=offset)
            sample_end = sample_start + timedelta(days=period_days)
            
            samples.append({
                'start': sample_start.strftime('%Y-%m-%d'),
                'end': sample_end.strftime('%Y-%m-%d')
            })
        
        return samples
    
    # ==================== Silver Bullet 回測 ====================
    
    def backtest_silver_bullet(self, df):
        """
        Silver Bullet 策略回測
        - 15m 時間框架
        - 時段限制：2-5am, 10-11am UTC
        - 盈虧比 1:2.5
        """
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        trades = []
        equity = self.initial_capital
        
        for i in range(210, len(df), 4):  # 每4根15m = 1小時
            current = df.iloc[i]
            prev_4h = df.iloc[i-4:i]
            
            if pd.isna(current.get('ema_200')):
                continue
            
            # 時段限制（UTC）
            hour = current['timestamp'].hour
            if not ((2 <= hour < 5) or (10 <= hour < 11)):
                continue
            
            signal = None
            sl = 0
            
            # 掃蕩形態
            lh_low = prev_4h['low'].min()
            if current['low'] < lh_low and current['close'] > lh_low:
                if current['close'] > current['ema_200']:
                    signal = 'LONG'
                    sl = current['low']
            
            lh_high = prev_4h['high'].max()
            if current['high'] > lh_high and current['close'] < lh_high:
                if current['close'] < current['ema_200']:
                    signal = 'SHORT'
                    sl = current['high']
            
            if signal:
                risk_amt = equity * 0.02
                risk_dist = abs(current['close'] - sl)
                
                if risk_dist == 0:
                    continue
                
                tp = current['close'] + (risk_dist * 2.5) if signal == 'LONG' else current['close'] - (risk_dist * 2.5)
                
                metrics = {'pnl': 0, 'result': 'OPEN'}
                
                future = df.iloc[i+1:i+100]
                for _, candle in future.iterrows():
                    if signal == 'LONG':
                        if candle['low'] <= sl:
                            metrics['pnl'] = -risk_amt
                            metrics['result'] = 'LOSS'
                            break
                        if candle['high'] >= tp:
                            metrics['pnl'] = risk_amt * 2.5
                            metrics['result'] = 'WIN'
                            break
                    else:
                        if candle['high'] >= sl:
                            metrics['pnl'] = -risk_amt
                            metrics['result'] = 'LOSS'
                            break
                        if candle['low'] <= tp:
                            metrics['pnl'] = risk_amt * 2.5
                            metrics['result'] = 'WIN'
                            break
                
                if metrics['result'] != 'OPEN':
                    equity += metrics['pnl']
                    trades.append(metrics)
        
        return self.calculate_metrics(trades, equity)
    
    # ==================== Hybrid SFP 回測 ====================
    
    def backtest_hybrid_sfp(self, df):
        """
        Hybrid SFP 策略回測
        - 4h 時間框架（需要從15m聚合）
        - ADX > 30, RSI 60/40
        - 盈虧比 1:2.5
        """
        # 從15m聚合到4h
        df_4h = self.resample_to_4h(df)
        
        df_4h['ema_200'] = ta.ema(df_4h['close'], length=200)
        df_4h['rsi'] = ta.rsi(df_4h['close'], length=14)
        df_4h['atr'] = ta.atr(df_4h['high'], df_4h['low'], df_4h['close'], length=14)
        df_4h['adx'] = ta.adx(df_4h['high'], df_4h['low'], df_4h['close'], length=14)['ADX_14']
        
        bb = ta.bbands(df_4h['close'], length=20, std=2.0)
        if bb is not None:
            cols = bb.columns
            df_4h['bb_upper'] = bb[cols[cols.str.startswith('BBU')][0]]
            df_4h['bb_lower'] = bb[cols[cols.str.startswith('BBL')][0]]
            df_4h['bw'] = bb[cols[cols.str.startswith('BBB')][0]]
        
        df_4h['swing_high'] = df_4h['high'].rolling(window=50).max().shift(1)
        df_4h['swing_low'] = df_4h['low'].rolling(window=50).min().shift(1)
        
        trades = []
        equity = self.initial_capital
        
        for i in range(250, len(df_4h)):
            prev = df_4h.iloc[i-1]
            
            if pd.isna(prev.get('adx')) or pd.isna(prev.get('rsi')):
                continue
            
            signal = None
            sl = 0
            
            # SFP
            if prev['adx'] > 30:
                if prev['high'] > prev['swing_high'] and prev['close'] < prev['swing_high']:
                    if prev['rsi'] > 60:
                        signal = 'SHORT'
                        sl = prev['high']
                elif prev['low'] < prev['swing_low'] and prev['close'] > prev['swing_low']:
                    if prev['rsi'] < 40:
                        signal = 'LONG'
                        sl = prev['low']
            
            # Trend
            if signal is None and pd.notna(prev.get('bb_upper')):
                if prev['adx'] > 25:
                    if prev['close'] > prev['bb_upper'] and prev['close'] > prev['ema_200'] and prev['bw'] > 5.0:
                        signal = 'LONG'
                        sl = prev['close'] - (2 * prev['atr'])
                    elif prev['close'] < prev['bb_lower'] and prev['close'] < prev['ema_200'] and prev['bw'] > 5.0:
                        signal = 'SHORT'
                        sl = prev['close'] + (2 * prev['atr'])
            
            if signal:
                risk_amt = equity * 0.02
                risk_dist = abs(prev['close'] - sl)
                
                if risk_dist == 0:
                    continue
                
                tp = prev['close'] + (risk_dist * 2.5) if signal == 'LONG' else prev['close'] - (risk_dist * 2.5)
                
                metrics = {'pnl': 0, 'result': 'OPEN'}
                
                future = df_4h.iloc[i:i+100]
                for _, candle in future.iterrows():
                    if signal == 'LONG':
                        if candle['low'] <= sl:
                            metrics['pnl'] = -risk_amt
                            metrics['result'] = 'LOSS'
                            break
                        if candle['high'] >= tp:
                            metrics['pnl'] = risk_amt * 2.5
                            metrics['result'] = 'WIN'
                            break
                    else:
                        if candle['high'] >= sl:
                            metrics['pnl'] = -risk_amt
                            metrics['result'] = 'LOSS'
                            break
                        if candle['low'] <= tp:
                            metrics['pnl'] = risk_amt * 2.5
                            metrics['result'] = 'WIN'
                            break
                
                if metrics['result'] != 'OPEN':
                    equity += metrics['pnl']
                    trades.append(metrics)
        
        return self.calculate_metrics(trades, equity)
    
    def resample_to_4h(self, df):
        """將15m數據聚合為4h"""
        df = df.set_index('timestamp')
        df_4h = df.resample('4H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        return df_4h
    
    # ==================== 統計計算 ====================
    
    def calculate_metrics(self, trades, equity):
        """計算回測指標"""
        if not trades:
            return None
        
        df = pd.DataFrame(trades)
        total_trades = len(trades)
        wins = len(df[df['result'] == 'WIN'])
        win_rate = (wins / total_trades) * 100
        total_return = ((equity - self.initial_capital) / self.initial_capital) * 100
        
        returns = [t['pnl'] / self.initial_capital for t in trades]
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'sharpe': sharpe,
            'final_equity': equity
        }
    
    def calculate_confidence_interval(self, values, confidence=0.95):
        """計算信賴區間"""
        n = len(values)
        mean = np.mean(values)
        std = np.std(values, ddof=1)
        se = std / np.sqrt(n)
        
        t_value = stats.t.ppf((1 + confidence) / 2, n - 1)
        margin = t_value * se
        
        return {
            'mean': mean,
            'std': std,
            'ci_lower': mean - margin,
            'ci_upper': mean + margin,
            'n': n
        }
    
    # ==================== 主執行流程 ====================
    
    def run_statistical_test(self, strategy_name, n_samples=20, use_api=False):
        """
        執行統計抽樣回測
        
        Args:
            strategy_name: 'silver_bullet' or 'hybrid_sfp'
            n_samples: 抽樣數量
            use_api: 是否從 API 抓取（False 則使用本地數據）
        """
        print("=" * 70)
        print(f"統計抽樣回測: {strategy_name}")
        print(f"抽樣數量: {n_samples} 個時間區間（每個3個月）")
        print(f"數據來源: {'幣安 API' if use_api else '本地數據'}")
        print("="*70)
        
        # 生成時間區間（擴展到 2020-2024）
        periods = self.generate_sample_periods('2020-01-01', '2024-06-30', n_samples, 3)
        
        results = []
        timeframe = '15m' if strategy_name == 'silver_bullet' else '15m'  # Hybrid 也用15m再聚合
        
        for i, period in enumerate(periods):
            print(f"\n區間 {i+1}/{n_samples}: {period['start']} ~ {period['end']}")
            
            if use_api:
                df = self.fetch_data(timeframe, period['start'], period['end'])
            else:
                # 使用本地數據（快速測試）
                df = self.load_local_data(timeframe, period['start'], period['end'])
            
            if df is None or len(df) < 500:
                print("  數據不足，跳過")
                continue
            
            # 執行回測
            if strategy_name == 'silver_bullet':
                result = self.backtest_silver_bullet(df)
            else:
                result = self.backtest_hybrid_sfp(df)
            
            if result:
                results.append(result)
                print(f"  結果: {result['total_trades']} 筆, 勝率 {result['win_rate']:.1f}%, 回報 {result['total_return']:+.2f}%")
        
        # 統計分析
        if results:
            self.generate_statistical_report(strategy_name, results)
        else:
            print("\n❌ 無有效結果")
    
    def load_local_data(self, timeframe, start, end):
        """從本地CSV載入數據（用於快速測試）"""
        try:
            df = pd.read_csv(f'data/backtest/BTC_USDT_{timeframe}_2023-2024.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            mask = (df['timestamp'] >= start) & (df['timestamp'] <= end)
            return df[mask]
        except:
            return None
    
    def generate_statistical_report(self, strategy_name, results):
        """生成統計報告"""
        print("\n" + "=" * 70)
        print("📊 統計分析結果 (95% 信賴區間)")
        print("=" * 70)
        
        # 提取各項指標
        returns = [r['total_return'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        sharpes = [r['sharpe'] for r in results]
        
        # 計算信賴區間
        returns_ci = self.calculate_confidence_interval(returns)
        win_rate_ci = self.calculate_confidence_interval(win_rates)
        sharpe_ci = self.calculate_confidence_interval(sharpes)
        
        print(f"\n總回報:")
        print(f"  平均: {returns_ci['mean']:.2f}%")
        print(f"  標準差: {returns_ci['std']:.2f}%")
        print(f"  95% CI: [{returns_ci['ci_lower']:.2f}%, {returns_ci['ci_upper']:.2f}%]")
        
        print(f"\n勝率:")
        print(f"  平均: {win_rate_ci['mean']:.2f}%")
        print(f"  標準差: {win_rate_ci['std']:.2f}%")
        print(f"  95% CI: [{win_rate_ci['ci_lower']:.2f}%, {win_rate_ci['ci_upper']:.2f}%]")
        
        print(f"\nSharpe Ratio:")
        print(f"  平均: {sharpe_ci['mean']:.2f}")
        print(f"  95% CI: [{sharpe_ci['ci_lower']:.2f}, {sharpe_ci['ci_upper']:.2f}]")
        
        print(f"\n樣本數: {len(results)}")
        
        # 穩健性評估
        positive_returns = sum(1 for r in returns if r > 0)
        consistency = (positive_returns / len(returns)) * 100
        
        print(f"\n穩健性:")
        print(f"  盈利區間比例: {consistency:.1f}% ({positive_returns}/{len(results)})")
        
        if consistency >= 70:
            print("  ✅ 策略穩健（70%+ 區間盈利）")
        elif consistency >= 50:
            print("  ⚠️ 策略一般（50-70% 區間盈利）")
        else:
            print("  ❌ 策略不穩定（<50% 區間盈利）")
        
        # ==================== 新增：穩健驗證器 ====================
        print("\n")
        from tools.robust_backtest_validator import RobustValidator
        
        validator = RobustValidator(n_bootstrap=1000, trim_percent=0.05)
        robust_results = validator.validate(returns)
        
        # 顯示穩健驗證報告
        print(validator.generate_report(robust_results, strategy_name))
        
        # 保存報告
        report_path = f"data/backtest/statistical_{strategy_name}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"統計抽樣回測報告: {strategy_name}\n")
            f.write("=" * 70 + "\n\n")
            
            # 基本統計
            f.write("【傳統 95% 信賴區間（t-test）】\n")
            f.write(f"樣本數: {len(results)}\n")
            f.write(f"總回報: {returns_ci['mean']:.2f}% ± {returns_ci['std']:.2f}%\n")
            f.write(f"95% CI: [{returns_ci['ci_lower']:.2f}%, {returns_ci['ci_upper']:.2f}%]\n")
            f.write(f"勝率: {win_rate_ci['mean']:.2f}% ± {win_rate_ci['std']:.2f}%\n")
            f.write(f"穩健性: {consistency:.1f}%\n\n")
            
            # 穩健驗證結果
            f.write(validator.generate_report(robust_results))
        
        print(f"\n📄 報告已保存: {report_path}")


def main():
    backtester = StatisticalBacktester('BTC/USDT')
    
    # 使用幣安 API 模式
    print("🌐 使用幣安 API 抓取歷史數據 (2020-2024)")
    print("⏱️  預計需要 30-60 分鐘（API 限制）\n")
    
    # Silver Bullet
    backtester.run_statistical_test('silver_bullet', n_samples=30, use_api=True)
    
    print("\n\n")
    
    # Hybrid SFP
    backtester.run_statistical_test('hybrid_sfp', n_samples=30, use_api=True)

if __name__ == "__main__":
    main()
