# 📂 Scripts 目錄說明

獨立工具腳本集合，用於分析、回測、維護等任務。

---

## 📊 analysis/

**市場分析與監控工具**

### `check_fg_panic.py`
恐慌檢測腳本，每天 3 次檢查市場狀態

**運行**：
```bash
python scripts/analysis/check_fg_panic.py
```

**功能**：
- 檢測 Fear & Greed < 20（恐慌）
- RSI < 30（超賣）
- 價格 < MA200（熊市）
- 符合條件時發送 Telegram 通知

**Cron 設置**：
```bash
# 每天早8點、下午2點、晚8點（UTC 0:00, 6:00, 12:00）
0 0,6,12 * * * cd /root/ai-crypto-bot && python3 scripts/analysis/check_fg_panic.py >> /var/log/fg_panic.log 2>&1
```

### `quick_analysis.py`
快速市場分析

**運行**：
```bash
python scripts/analysis/quick_analysis.py
```

### `dashboard_unified.py`
統一儀表板（舊版，已廢棄）

---

## 🧪 backtests/

**回測驗證工具**

### `comprehensive_dca_backtest.py`
完整 DCA 策略回測

**運行**：
```bash
python scripts/backtests/comprehensive_dca_backtest.py
```

**輸出**：多種 DCA 策略的績效對比

### `final_system_backtest.py`
最終系統回測

### `robust_backtest_validator.py`
穩健性驗證回測

### `statistical_backtest.py`
統計分析回測（包含蒙地卡羅模擬）

### `verify_three_strategies.py`
三策略對比驗證

### `compare_with_dca.py`
與普通 DCA 對比

---

## 🔧 maintenance/

**維護與檢查工具**

### `backup_database.py`
數據庫備份工具

**運行**：
```bash
python scripts/maintenance/backup_database.py
```

### `check_context.py`
檢查系統上下文

### `check_models.py`
檢查模型狀態

### `check_recent_signals.py`
檢查最近信號

**運行**：
```bash
python scripts/maintenance/check_recent_signals.py
```

---

## 🤖 ai/

**AI 相關工具**

### `ai_performance_reporter.py`
AI 績效報告生成器

### `ai_symbol_advisor.py`
AI 幣種建議工具

---

## 🎯 selectors/

**幣種選擇器**

### `dynamic_market_cap_selector.py`
動態市值選擇器

**功能**：根據市值動態選擇交易幣種

### `dynamic_symbol_selector.py`
動態幣種選擇器

**功能**：根據多因素選擇最佳交易標的

---

## 💡 使用建議

### 開發時
- 使用 `analysis/` 工具快速檢查市場狀態
- 使用 `backtests/` 驗證策略變更

### 生產環境
- `check_fg_panic.py` 透過 Cron 定時執行
- 定期運行 `backup_database.py` 備份數據

### 故障排除
- 使用 `maintenance/` 下的工具診斷問題
- 檢查 `check_recent_signals.py` 確認信號正常

---

## 📝 注意事項

1. **路徑問題**：所有腳本應從專案根目錄運行
2. **依賴管理**：確保已安裝 `requirements.txt` 中的所有依賴
3. **環境變數**：需要 `.env` 文件配置 API keys
4. **日誌輸出**：生產環境建議重定向到日誌文件
