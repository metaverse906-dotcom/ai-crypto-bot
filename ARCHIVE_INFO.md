# Archive 資料夾說明

此專案的 `archive/` 資料夾包含研究、測試與臨時文件，不會部署到生產環境。

## 📁 已封存內容

### 回測腳本（`archive/research_backtests/`）
- `academic_momentum_backtest.py` - 學術級動能策略回測
- `professional_momentum_backtest.py` - 專業版動能回測  
- `final_momentum_backtest.py` - 最終動能策略回測
- `analyze_mvrv_momentum.py` - MVRV 動能分析工具
- `fetch_recent_btc_data.py` - 歷史數據獲取

### 回測結果（`archive/temp_results/`）
- `academic_results.txt` - 學術版回測結果
- `pro_results.txt` - 專業版回測結果
- `final_results.txt` - 最終回測結果  
- `mvrv_momentum_results.txt` - 動能分析結果
- `backtest_results.txt` - 其他回測結果

## 🎯 研究結論

經過 6+ 種賣出策略測試（2020-2025 真實數據回測）：

| 策略 | vs 原系統 | vs HODL | 狀態 |
|------|-----------|---------|------|
| 階梯式賣出 | -9.7% | -42.6% | ❌ 封存 |
| 1.5x ATH | -42% | -53% | ❌ 封存 |
| RSI + 回調 | -1.0% | -33.5% | ❌ 封存 |
| 簡化動能 | -2.8% | -34.8% | ❌ 封存 |
| 專業動能 | +0.5% | -32.5% | ❌ 封存 |
| **學術動能** | **+1.7%** | **-31.8%** | **✅ 已採用** |

## ✅ 最終實施方案

**學術級 MVRV 動能策略**（已整合到生產系統）：
- ✅ 14 日 EMA 平滑 MVRV Z-Score
- ✅ 7 日線性回歸斜率計算
- ✅ 三階段動能檢測（上升/高原/下跌）
- ✅ 動態 DCA Out 公式
- ✅ 監控模式運行（Telegram 顯示，手動執行）

**模組位置**：
- `core/mvrv_momentum_analyzer.py` - 動能分析器
- `bot/handlers/mvrv_dca_analyzer.py` - 已整合

## 📝 為什麼保留 Archive？

這些文件記錄了完整的研究與決策過程：
1. 證明最終方案是經過系統驗證的
2. 提供未來優化的參考基準
3. 記錄失敗嘗試，避免重複犯錯
4. 展示 DCA 策略優化的極限

**建議保留但不部署到生產環境。**
