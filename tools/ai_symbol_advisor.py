#!/usr/bin/env python3
# tools/ai_symbol_advisor.py
"""
AI 币种顾问（可选增强）
使用 Gemini AI 分析市场并提供建议
"""

import os
from datetime import datetime


class AISymbolAdvisor:
    """AI 币种顾问"""
    
    def __init__(self):
        try:
            import google.generativeai as genai
            api_key = os.getenv('GEMINI_API_KEY', '')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                self.enabled = True
            else:
                self.enabled = False
        except:
            self.enabled = False
    
    def analyze_selection(self, quantitative_results):
        """用 AI 分析量化选币结果"""
        if not self.enabled:
            return "AI 分析未启用（需设置 GEMINI_API_KEY）"
        
        # 构建提示
        symbols_info = "\n".join([
            f"- {m['symbol']}: 总分{m['total_score']:.1f}, 波动{m['volatility']:.1f}%, "
            f"流动性{m['volume_score']:.1f}, 趋势{m['trend_score']:.1f}"
            for m in quantitative_results[:10]
        ])
        
        prompt = f"""
你是专业的加密货币分析师。基于以下量化评分结果，请提供专业建议：

量化评分 Top 10:
{symbols_info}

请分析：
1. 这个选择是否合理？有无需要调整的？
2. 当前市场环境（牛市/熊市/震荡）
3. 建议关注的新兴币种（如果有）
4. 风险提示

请用繁体中文，简洁回答（150字内）。
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI 分析失败: {e}"


def main():
    """测试 AI 顾问"""
    advisor = AISymbolAdvisor()
    
    # 模拟量化结果
    mock_results = [
        {'symbol': 'BTC/USDT', 'total_score': 92.5, 'volatility': 70, 
         'volume_score': 98, 'trend_score': 85},
        {'symbol': 'ETH/USDT', 'total_score': 88.3, 'volatility': 80, 
         'volume_score': 95, 'trend_score': 82},
    ]
    
    if advisor.enabled:
        analysis = advisor.analyze_selection(mock_results)
        print("AI 分析:")
        print(analysis)
    else:
        print("AI 未启用，仅使用量化评分")


if __name__ == "__main__":
    main()
