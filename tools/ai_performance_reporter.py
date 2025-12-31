#!/usr/bin/env python3
# tools/ai_performance_reporter.py
"""
AI 驅動的績效報告生成器
使用 Gemini AI 分析交易數據並生成洞察
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import google.generativeai as genai
    from core.database import db
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False


class AIPerformanceReporter:
    """AI 績效報告生成器"""
    
    def __init__(self):
        self.ai_enabled = False
        
        if GEMINI_AVAILABLE:
            api_key = os.getenv('GEMINI_API_KEY', '')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                self.ai_enabled = True
    
    def generate_daily_report(self) -> str:
        """生成每日績效報告"""
        # 獲取今日數據
        today = datetime.now().date()
        trades = db.get_trades_by_date_range(str(today), str(today))
        
        if not trades:
            return "📊 今日暫無交易"
        
        df = pd.DataFrame(trades)
        
        # 基礎統計
        stats = {
            'total_trades': len(df),
            'wins': len(df[df['pnl'] > 0]) if 'pnl' in df.columns else 0,
            'losses': len(df[df['pnl'] < 0]) if 'pnl' in df.columns else 0,
            'total_pnl': df['pnl'].sum() if 'pnl' in df.columns else 0,
            'win_rate': len(df[df['pnl'] > 0]) / len(df) * 100 if 'pnl' in df.columns and len(df) > 0 else 0
        }
        
        # 生成報告
        report = f"""
📊 每日績效報告 - {today}

交易統計：
- 總交易次數：{stats['total_trades']}
- 獲利筆數：{stats['wins']}
- 虧損筆數：{stats['losses']}
- 勝率：{stats['win_rate']:.1f}%
- 總盈虧：${stats['total_pnl']:.2f}
"""
        
        # 如果有 AI，加入分析
        if self.ai_enabled and len(df) > 0:
            ai_insight = self._get_ai_insight(df, stats, period='daily')
            report += f"\n🤖 AI 分析：\n{ai_insight}\n"
        
        return report
    
    def generate_weekly_report(self) -> str:
        """生成每週績效報告"""
        # 獲取過去 7 天數據
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        trades = db.get_trades_by_date_range(str(start_date), str(end_date))
        
        if not trades:
            return "📊 本週暫無交易"
        
        df = pd.DataFrame(trades)
        
        # 基礎統計
        stats = {
            'total_trades': len(df),
            'wins': len(df[df['pnl'] > 0]) if 'pnl' in df.columns else 0,
            'total_pnl': df['pnl'].sum() if 'pnl' in df.columns else 0,
            'win_rate': len(df[df['pnl'] > 0]) / len(df) * 100 if 'pnl' in df.columns and len(df) > 0 else 0,
            'avg_pnl': df['pnl'].mean() if 'pnl' in df.columns else 0
        }
        
        report = f"""
📊 每週績效報告 ({start_date} - {end_date})

交易統計：
- 總交易次數：{stats['total_trades']}
- 勝率：{stats['win_rate']:.1f}%
- 總盈虧：${stats['total_pnl']:.2f}
- 平均每筆：${stats['avg_pnl']:.2f}
"""
        
        # AI 分析
        if self.ai_enabled and len(df) > 0:
            ai_insight = self._get_ai_insight(df, stats, period='weekly')
            report += f"\n🤖 AI 分析與建議：\n{ai_insight}\n"
        
        return report
    
    def _get_ai_insight(self, df, stats, period='daily'):
        """使用 AI 生成洞察"""
        if not self.ai_enabled:
            return "（AI 功能未啟用）"
        
        # 構建分析數據
        data_summary = f"""
時期：{period}
交易數據：
- 總交易：{stats['total_trades']}
- 勝率：{stats['win_rate']:.1f}%
- 總盈虧：${stats['total_pnl']:.2f}

前5筆交易：
{df.head(5)[['symbol', 'side', 'pnl', 'close_reason']].to_string() if len(df) > 0 else '無'}
"""
        
        prompt = f"""
你是一個專業的加密貨幣交易分析師。基於以下交易數據，請提供簡潔的分析（3-5點）：

{data_summary}

請分析：
1. 績效評估（好/一般/需改進）
2. 主要問題或優勢
3. 明天/下週建議觀察的標的或方向
4. 風險提示

請用繁體中文，保持簡潔（200字內）。
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"（AI 分析失敗：{e}）"


def main():
    reporter = AIPerformanceReporter()
    
    print("=" * 70)
    print("📊 AI 績效報告生成器")
    print("=" * 70)
    
    if not reporter.ai_enabled:
        print("\n⚠️  AI 功能未啟用")
        print("   設置環境變量 GEMINI_API_KEY 以啟用 AI 分析")
    
    print("\n" + reporter.generate_daily_report())
    print("\n" + "=" * 70)
    print("\n" + reporter.generate_weekly_report())


if __name__ == "__main__":
    main()
