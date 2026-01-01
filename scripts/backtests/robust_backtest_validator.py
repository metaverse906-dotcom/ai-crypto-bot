#!/usr/bin/env python3
# tools/robust_backtest_validator.py
"""
穩健回測驗證器
- Bootstrap 重抽樣（不假設常態分佈）
- Trimmed Mean 分析（去除極端值）
- 最差情境分析
- 穩健性評分系統
"""

import numpy as np
from scipy import stats
from typing import List, Dict, Any


class RobustValidator:
    """
    穩健回測驗證器
    解決 95% CI 假設常態分佈與極端值依賴的問題
    """
    
    def __init__(self, n_bootstrap: int = 1000, trim_percent: float = 0.05):
        """
        Args:
            n_bootstrap: Bootstrap 重抽樣次數
            trim_percent: 修剪比例（兩端各去除的百分比）
        """
        self.n_bootstrap = n_bootstrap
        self.trim_percent = trim_percent
    
    # ==================== 主驗證介面 ====================
    
    def validate(self, returns: List[float]) -> Dict[str, Any]:
        """
        執行完整的穩健性驗證
        
        Args:
            returns: 回報率列表（%）
            
        Returns:
            包含所有驗證結果的字典
        """
        if not returns or len(returns) < 10:
            return {
                'error': '樣本數不足（需要至少 10 個）',
                'robustness_score': 0,
                'rating': 'INSUFFICIENT_DATA'
            }
        
        returns_array = np.array(returns)
        
        # 1. Bootstrap 分析
        bootstrap_ci = self._bootstrap_confidence_interval(returns_array)
        
        # 2. Trimmed Mean 分析
        trimmed_stats = self._trimmed_analysis(returns_array)
        
        # 3. 最差情境分析
        worst_case = self._worst_case_analysis(returns_array)
        
        # 4. 分佈特性分析
        distribution = self._distribution_analysis(returns_array)
        
        # 5. 穩健性評分
        robustness_score, rating = self._calculate_robustness_score(
            returns_array, bootstrap_ci, trimmed_stats, worst_case
        )
        
        return {
            'bootstrap_ci': bootstrap_ci,
            'trimmed_stats': trimmed_stats,
            'worst_case': worst_case,
            'distribution': distribution,
            'robustness_score': robustness_score,
            'rating': rating,
            'sample_size': len(returns)
        }
    
    # ==================== Bootstrap 重抽樣 ====================
    
    def _bootstrap_confidence_interval(
        self, 
        returns: np.ndarray, 
        confidence: float = 0.95
    ) -> Dict[str, float]:
        """
        Bootstrap 95% 信賴區間（不假設分佈）
        """
        bootstrap_means = []
        n = len(returns)
        
        for _ in range(self.n_bootstrap):
            # 有放回抽樣
            sample = np.random.choice(returns, size=n, replace=True)
            bootstrap_means.append(np.mean(sample))
        
        # 計算百分位數
        alpha = 1 - confidence
        ci_lower = np.percentile(bootstrap_means, (alpha/2) * 100)
        ci_upper = np.percentile(bootstrap_means, (1 - alpha/2) * 100)
        
        return {
            'mean': np.mean(bootstrap_means),
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'std': np.std(bootstrap_means),
            'method': 'Bootstrap'
        }
    
    # ==================== Trimmed Mean 分析 ====================
    
    def _trimmed_analysis(self, returns: np.ndarray) -> Dict[str, float]:
        """
        去除極端值的穩健統計
        """
        n = len(returns)
        trim_count = int(n * self.trim_percent)
        
        # 排序後去除兩端
        sorted_returns = np.sort(returns)
        trimmed_returns = sorted_returns[trim_count:n-trim_count]
        
        # 計算修剪後的統計量
        trimmed_mean = np.mean(trimmed_returns)
        trimmed_std = np.std(trimmed_returns, ddof=1)
        
        # 與完整樣本比較
        full_mean = np.mean(returns)
        impact = ((trimmed_mean - full_mean) / full_mean * 100) if full_mean != 0 else 0
        
        # 極端值統計
        removed_top = sorted_returns[-trim_count:] if trim_count > 0 else np.array([])
        removed_bottom = sorted_returns[:trim_count] if trim_count > 0 else np.array([])
        
        return {
            'trimmed_mean': trimmed_mean,
            'trimmed_std': trimmed_std,
            'full_mean': full_mean,
            'impact_percent': impact,
            'top_extremes_mean': np.mean(removed_top) if len(removed_top) > 0 else 0,
            'bottom_extremes_mean': np.mean(removed_bottom) if len(removed_bottom) > 0 else 0,
            'trim_percent': self.trim_percent * 100
        }
    
    # ==================== 最差情境分析 ====================
    
    def _worst_case_analysis(self, returns: np.ndarray) -> Dict[str, float]:
        """
        分析最差 10% 的樣本表現
        """
        n = len(returns)
        worst_n = max(1, int(n * 0.1))
        
        sorted_returns = np.sort(returns)
        worst_10_percent = sorted_returns[:worst_n]
        
        # 連續虧損分析
        negative_returns = returns[returns < 0]
        max_consecutive_losses = self._max_consecutive_negative(returns)
        
        return {
            'worst_10_mean': np.mean(worst_10_percent),
            'worst_10_std': np.std(worst_10_percent, ddof=1) if len(worst_10_percent) > 1 else 0,
            'worst_single': np.min(returns),
            'negative_count': len(negative_returns),
            'negative_percent': (len(negative_returns) / n) * 100,
            'max_consecutive_losses': max_consecutive_losses,
            'worst_10_sample_size': len(worst_10_percent)
        }
    
    def _max_consecutive_negative(self, returns: np.ndarray) -> int:
        """計算最大連續虧損次數"""
        max_streak = 0
        current_streak = 0
        
        for r in returns:
            if r < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    # ==================== 分佈特性分析 ====================
    
    def _distribution_analysis(self, returns: np.ndarray) -> Dict[str, float]:
        """
        分析收益分佈特性
        """
        # 偏度（Skewness）：正值=右偏（少數大獲利）
        skewness = stats.skew(returns)
        
        # 峰度（Kurtosis）：>3 = 肥尾分佈
        kurtosis = stats.kurtosis(returns, fisher=False)  # Pearson's definition
        
        # Jarque-Bera 常態性檢驗
        jb_stat, jb_pvalue = stats.jarque_bera(returns)
        is_normal = jb_pvalue > 0.05  # p > 0.05 接受常態假設
        
        return {
            'skewness': skewness,
            'kurtosis': kurtosis,
            'is_normal_distribution': is_normal,
            'jb_pvalue': jb_pvalue,
            'distribution_type': self._classify_distribution(skewness, kurtosis, is_normal)
        }
    
    def _classify_distribution(self, skew: float, kurt: float, is_normal: bool) -> str:
        """分類分佈類型"""
        if is_normal:
            return 'Normal'
        elif abs(skew) > 1 and kurt > 5:
            return 'Fat-Tailed (Extreme Events)'
        elif skew > 0.5:
            return 'Right-Skewed (Few Large Wins)'
        elif skew < -0.5:
            return 'Left-Skewed (Few Large Losses)'
        elif kurt > 5:
            return 'Heavy-Tailed'
        else:
            return 'Non-Normal'
    
    # ==================== 穩健性評分 ====================
    
    def _calculate_robustness_score(
        self,
        returns: np.ndarray,
        bootstrap_ci: Dict,
        trimmed_stats: Dict,
        worst_case: Dict
    ) -> tuple[float, str]:
        """
        計算穩健性評分（0-100）
        
        評分標準：
        - 30 分：Bootstrap CI 下界為正
        - 25 分：Trimmed Mean 為正
        - 20 分：最差 10% 樣本不過度虧損
        - 15 分：正報酬區間比例高
        - 10 分：最大連續虧損可控
        """
        score = 0.0
        
        # 1. Bootstrap CI 下界 (30 分)
        if bootstrap_ci['ci_lower'] > 0:
            score += 30
        elif bootstrap_ci['ci_lower'] > -5:
            score += 15
        
        # 2. Trimmed Mean (25 分)
        if trimmed_stats['trimmed_mean'] > 0:
            score += 25
        elif trimmed_stats['trimmed_mean'] > -5:
            score += 12
        
        # 3. 最差 10% 樣本 (20 分)
        worst_mean = worst_case['worst_10_mean']
        if worst_mean > -10:
            score += 20
        elif worst_mean > -20:
            score += 10
        elif worst_mean > -30:
            score += 5
        
        # 4. 正報酬比例 (15 分)
        positive_percent = 100 - worst_case['negative_percent']
        if positive_percent >= 70:
            score += 15
        elif positive_percent >= 50:
            score += 10
        elif positive_percent >= 40:
            score += 5
        
        # 5. 最大連續虧損 (10 分)
        max_losses = worst_case['max_consecutive_losses']
        if max_losses <= 3:
            score += 10
        elif max_losses <= 5:
            score += 7
        elif max_losses <= 7:
            score += 4
        
        # 評級
        if score >= 80:
            rating = 'Excellent ⭐⭐⭐⭐⭐'
        elif score >= 65:
            rating = 'Good ⭐⭐⭐⭐'
        elif score >= 50:
            rating = 'Fair ⭐⭐⭐'
        elif score >= 35:
            rating = 'Poor ⭐⭐'
        else:
            rating = 'Very Poor ⭐'
        
        return score, rating
    
    # ==================== 報告生成 ====================
    
    def generate_report(self, results: Dict[str, Any], strategy_name: str = '') -> str:
        """
        生成文字報告
        """
        if 'error' in results:
            return f"❌ {results['error']}"
        
        report = []
        report.append("=" * 70)
        report.append(f"🔒 穩健性驗證報告{' - ' + strategy_name if strategy_name else ''}")
        report.append("=" * 70)
        
        # Bootstrap CI
        bs = results['bootstrap_ci']
        report.append(f"\n📊 Bootstrap 信賴區間（{self.n_bootstrap} 次重抽樣）：")
        report.append(f"  平均: {bs['mean']:.2f}%")
        report.append(f"  95% CI: [{bs['ci_lower']:.2f}%, {bs['ci_upper']:.2f}%]")
        report.append(f"  標準差: {bs['std']:.2f}%")
        
        # Trimmed Mean
        tm = results['trimmed_stats']
        report.append(f"\n📉 去除極端值分析（修剪 {tm['trim_percent']:.0f}%）：")
        report.append(f"  完整樣本平均: {tm['full_mean']:.2f}%")
        report.append(f"  修剪後平均: {tm['trimmed_mean']:.2f}%")
        report.append(f"  極端值影響: {tm['impact_percent']:+.2f}%")
        if abs(tm['impact_percent']) > 20:
            report.append(f"  ⚠️ 策略高度依賴極端值")
        
        # Worst Case
        wc = results['worst_case']
        report.append(f"\n⚠️ 最差情境分析：")
        report.append(f"  最差 10% 平均: {wc['worst_10_mean']:.2f}%")
        report.append(f"  最差單次: {wc['worst_single']:.2f}%")
        report.append(f"  負報酬比例: {wc['negative_percent']:.1f}%")
        report.append(f"  最大連續虧損: {wc['max_consecutive_losses']} 次")
        
        # Distribution
        dist = results['distribution']
        report.append(f"\n📐 分佈特性：")
        report.append(f"  類型: {dist['distribution_type']}")
        report.append(f"  偏度: {dist['skewness']:.2f}")
        report.append(f"  峰度: {dist['kurtosis']:.2f}")
        if not dist['is_normal_distribution']:
            report.append(f"  ⚠️ 非常態分佈（t-test 可能不準確）")
        
        # Robustness Score
        report.append(f"\n🎯 穩健性評分：")
        report.append(f"  分數: {results['robustness_score']:.1f}/100")
        report.append(f"  評級: {results['rating']}")
        report.append(f"  樣本數: {results['sample_size']}")
        
        report.append("=" * 70)
        
        return "\n".join(report)


# ==================== 測試函數 ====================

def test_validator():
    """測試驗證器功能"""
    print("🧪 測試穩健回測驗證器\n")
    
    validator = RobustValidator(n_bootstrap=1000)
    
    # 測試 1: 常態分佈
    print("測試 1: 常態分佈數據")
    normal_returns = np.random.normal(10, 20, 100).tolist()
    result1 = validator.validate(normal_returns)
    print(validator.generate_report(result1, "Normal Distribution Test"))
    
    print("\n\n")
    
    # 測試 2: 肥尾分佈（模擬真實交易）
    print("測試 2: 肥尾分佈（模擬真實策略）")
    fat_tail_returns = np.concatenate([
        np.random.normal(-3, 8, 70),    # 70% 小虧損/小獲利
        np.random.normal(15, 15, 20),   # 20% 中等獲利
        np.random.normal(80, 40, 10)    # 10% 大獲利（極端值）
    ]).tolist()
    result2 = validator.validate(fat_tail_returns)
    print(validator.generate_report(result2, "Fat-Tail Distribution Test"))


if __name__ == "__main__":
    test_validator()
