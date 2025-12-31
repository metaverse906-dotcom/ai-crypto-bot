#!/usr/bin/env python3
"""
測試改良版回測驗證系統
使用簡化的模擬數據驗證新功能
"""

import sys
sys.path.append('.')

from robust_backtest_validator import RobustValidator
import numpy as np

def test_robust_validator():
    """測試穩健驗證器的各項功能"""
    
    print("=" * 70)
    print("🧪 測試改良版回測驗證系統")
    print("=" * 70)
    
    validator = RobustValidator(n_bootstrap=1000, trim_percent=0.05)
    
    # ==================== 測試 1: 常態分佈 ====================
    print("\n\n【測試 1】常態分佈數據（理想情況）")
    print("-" * 70)
    
    normal_returns = np.random.normal(15, 20, 50).tolist()
    result1 = validator.validate(normal_returns)
    print(validator.generate_report(result1, "Normal Distribution"))
    
    # ==================== 測試 2: 肥尾分佈 ====================
    print("\n\n【測試 2】肥尾分佈（真實交易策略模擬）")
    print("-" * 70)
    
    # 模擬：70% 小虧損/小獲利，20% 中等獲利，10% 大獲利
    fat_tail_returns = np.concatenate([
        np.random.normal(-5, 10, 35),   # 70% 小波動
        np.random.normal(20, 15, 10),   # 20% 中等獲利
        np.random.normal(80, 30, 5)     # 10% 大獲利（極端值）
    ]).tolist()
    
    result2 = validator.validate(fat_tail_returns)
    print(validator.generate_report(result2, "Fat-Tail Distribution"))
    
    # ==================== 測試 3: 極端依賴型 ====================
    print("\n\n【測試 3】高度依賴極端值（不穩健策略）")
    print("-" * 70)
    
    # 模擬：大量虧損但少數極端獲利
    extreme_returns = np.concatenate([
        np.random.normal(-8, 5, 40),    # 80% 虧損
        np.random.normal(200, 100, 10)  # 20% 極端獲利
    ]).tolist()
    
    result3 = validator.validate(extreme_returns)
    print(validator.generate_report(result3, "Extreme-Dependent"))
    
    # ==================== 總結對比 ====================
    print("\n\n" + "=" * 70)
    print("📊 三種策略對比總結")
    print("=" * 70)
    
    print(f"\n{'策略類型':<25} {'穩健性評分':<15} {'評級':<20} {'Trimmed Mean':<15}")
    print("-" * 70)
    print(f"{'1. 常態分佈 (理想)':<25} {result1['robustness_score']:<15.1f} {result1['rating']:<20} {result1['trimmed_stats']['trimmed_mean']:+.2f}%")
    print(f"{'2. 肥尾分佈 (真實)':<25} {result2['robustness_score']:<15.1f} {result2['rating']:<20} {result2['trimmed_stats']['trimmed_mean']:+.2f}%")
    print(f"{'3. 極端依賴 (不穩健)':<25} {result3['robustness_score']:<15.1f} {result3['rating']:<20} {result3['trimmed_stats']['trimmed_mean']:+.2f}%")
    
    print("\n" + "=" * 70)
    print("✅ 測試完成")
    print("=" * 70)
    
    print("\n💡 關鍵洞察：")
    print("  - Bootstrap CI 比傳統 t-test 更穩健（不假設常態分佈）")
    print("  - Trimmed Mean 揭示去除極端值後的真實表現")
    print("  - 穩健性評分綜合評估策略可靠性")
    print("  - 如果 Trimmed Mean 與完整平均差異大 → 策略過度依賴極端值")

if __name__ == "__main__":
    test_robust_validator()
