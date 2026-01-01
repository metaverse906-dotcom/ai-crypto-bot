#!/usr/bin/env python3
# tools/dynamic_symbol_selector.py
"""
动态币种选择器
基于量化指标 + AI 分析，每周自动评估和更新监控币种
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


class DynamicSymbolSelector:
    """动态币种选择器"""
    
    def __init__(self, top_n=30, select_n=5):
        self.exchange = ccxt.binance()
        self.top_n = top_n  # 评估前 N 名
        self.select_n = select_n  # 选择 N 个币种
    
    def get_candidate_symbols(self):
        """获取候选币种（市值 Top N）"""
        # 幣安热门币种（市值 Top 30）
        candidates = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
            'ADA/USDT', 'AVAX/USDT', 'DOGE/USDT', 'MATIC/USDT', 'DOT/USDT',
            'TRX/USDT', 'LINK/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT',
            'BCH/USDT', 'XLM/USDT', 'ETC/USDT', 'ICP/USDT', 'FIL/USDT',
            'APT/USDT', 'HBAR/USDT', 'ARB/USDT', 'OP/USDT', 'NEAR/USDT',
            'VET/USDT', 'AAVE/USDT', 'ALGO/USDT', 'GRT/USDT', 'SAND/USDT'
        ]
        
        # 过滤：確保有 4h K線和永續合約
        valid_symbols = []
        for symbol in candidates:
            try:
                # 测试是否能获取数据
                self.exchange.fetch_ohlcv(symbol, '4h', limit=5)
                valid_symbols.append(symbol)
            except:
                continue
        
        return valid_symbols[:self.top_n]
    
    def calculate_metrics(self, symbol, days=30):
        """计算币种评分指标"""
        try:
            # 获取历史数据
            ohlcv = self.exchange.fetch_ohlcv(symbol, '4h', limit=days*6)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 1. 波动率评分（60-100% 最佳）
            returns = df['close'].pct_change()
            volatility = returns.std() * np.sqrt(365*6) * 100  # 年化波动率
            
            if 60 <= volatility <= 100:
                vol_score = 100
            elif volatility < 60:
                vol_score = max(0, volatility / 60 * 100)
            else:  # > 100
                vol_score = max(0, 100 - (volatility - 100) / 2)
            
            # 2. 流动性评分（交易量）
            avg_volume = df['volume'].mean()
            volume_score = min(100, (avg_volume / 1e7) * 10)  # 归一化
            
            # 3. 趋势强度评分（ADX 概念）
            high_low_range = (df['high'] - df['low']).mean()
            trend_score = min(100, (high_low_range / df['close'].mean()) * 1000)
            
            # 4. 近期表现（过去 7 天收益）
            recent_return = (df['close'].iloc[-1] / df['close'].iloc[-42] - 1) * 100  # 7天
            performance_score = 50 + recent_return * 2  # 中心化到 50
            performance_score = max(0, min(100, performance_score))
            
            # 5. 价格稳定性（避免暴涨暴跌）
            price_changes = df['close'].pct_change().abs()
            max_daily_change = price_changes.nlargest(5).mean()  # 前5大波动平均
            stability_score = max(0, 100 - max_daily_change * 500)
            
            return {
                'symbol': symbol,
                'volatility': round(volatility, 2),
                'vol_score': round(vol_score, 2),
                'volume_score': round(volume_score, 2),
                'trend_score': round(trend_score, 2),
                'performance_score': round(performance_score, 2),
                'stability_score': round(stability_score, 2),
                'avg_volume': avg_volume
            }
        
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None
    
    def rank_symbols(self, metrics_list):
        """综合评分并排名"""
        # 权重配置
        weights = {
            'vol_score': 0.25,        # 波动率 25%
            'volume_score': 0.30,     # 流动性 30%（最重要）
            'trend_score': 0.20,      # 趋势 20%
            'performance_score': 0.15, # 表现 15%
            'stability_score': 0.10    # 稳定性 10%
        }
        
        for metrics in metrics_list:
            total_score = sum(
                metrics[key] * weight 
                for key, weight in weights.items()
            )
            metrics['total_score'] = round(total_score, 2)
        
        # 排序
        metrics_list.sort(key=lambda x: x['total_score'], reverse=True)
        return metrics_list
    
    def select_top_symbols(self, ranked_metrics):
        """选择 Top N 币种"""
        # 强制包含 BTC 和 ETH
        must_have = ['BTC/USDT', 'ETH/USDT']
        selected = []
        
        # 先加入必选币种
        for symbol in must_have:
            for metrics in ranked_metrics:
                if metrics['symbol'] == symbol:
                    selected.append(metrics)
                    break
        
        # 再从排名中选择剩余的
        for metrics in ranked_metrics:
            if metrics['symbol'] not in must_have:
                selected.append(metrics)
                if len(selected) >= self.select_n:
                    break
        
        return selected[:self.select_n]
    
    def generate_report(self, selected_symbols, all_metrics):
        """生成报告"""
        report = []
        report.append("="*70)
        report.append("动态币种选择报告")
        report.append("="*70)
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n【已选币种】 (Top {self.select_n})")
        
        for i, metrics in enumerate(selected_symbols, 1):
            report.append(f"\n{i}. {metrics['symbol']}")
            report.append(f"   总分: {metrics['total_score']:.1f}/100")
            report.append(f"   波动率: {metrics['volatility']:.1f}% (得分: {metrics['vol_score']:.1f})")
            report.append(f"   流动性: {metrics['volume_score']:.1f}")
            report.append(f"   趋势: {metrics['trend_score']:.1f}")
            report.append(f"   表现: {metrics['performance_score']:.1f}")
        
        report.append(f"\n\n【候补币种】 (Rank {self.select_n+1}-{self.select_n+5})")
        for i, metrics in enumerate(all_metrics[self.select_n:self.select_n+5], self.select_n+1):
            report.append(f"\n{i}. {metrics['symbol']}: {metrics['total_score']:.1f}/100")
        
        return '\n'.join(report)
    
    def save_config(self, selected_symbols, filename='config/symbols.json'):
        """保存选择的币种到配置文件"""
        config = {
            'last_update': datetime.now().isoformat(),
            'symbols': [m['symbol'] for m in selected_symbols],
            'metrics': selected_symbols
        }
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✅ 配置已保存到: {filename}")
    
    def run(self):
        """执行完整流程"""
        print("开始动态币种评估...\n")
        
        # 1. 获取候选
        candidates = self.get_candidate_symbols()
        print(f"✅ 找到 {len(candidates)} 个候选币种")
        
        # 2. 计算指标
        print(f"⏳ 分析币种指标...")
        metrics_list = []
        for symbol in candidates:
            metrics = self.calculate_metrics(symbol)
            if metrics:
                metrics_list.append(metrics)
        
        # 3. 排名
        ranked = self.rank_symbols(metrics_list)
        
        # 4. 选择
        selected = self.select_top_symbols(ranked)
        
        # 5. 生成报告
        report = self.generate_report(selected, ranked)
        print(report)
        
        # 6. 保存配置
        self.save_config(selected)
        
        return [m['symbol'] for m in selected]


if __name__ == "__main__":
    selector = DynamicSymbolSelector(top_n=30, select_n=5)
    selected_symbols = selector.run()
    
    print(f"\n🎯 建议监控币种:")
    for symbol in selected_symbols:
        print(f"   - {symbol}")
