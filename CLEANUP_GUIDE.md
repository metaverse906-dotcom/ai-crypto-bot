# 專案清理腳本

## 需要封存的文件（移到 archived/）

### 回測結果文件（舊的）
- backtest_results.txt
- backtest_results_detailed.txt
- dca_comparison_result.txt
- dca_results.txt
- silver_bullet_fixed_results.txt
- silver_bullet_results.txt
- smc_comparison_results.txt
- temp_backtest_lab.txt
- multi_symbols_result.txt
- result.txt

### 臨時文件
- temp_btc_recent.csv

### 舊的儀表板（如果不再使用）
- dashboard.py（如果只用 dashboard_unified.py）
- dashboard_realtime.py（如果不再使用）

## 建議目錄結構

```
ai-crypto-bot/
├── archived/           # 新增：封存目錄
│   ├── backtest_results/  # 舊的回測結果
│   └── deprecated_dashboards/  # 舊的儀表板
├── bot/               # ✅ 保留
├── config/            # ✅ 保留
├── core/              # ✅ 保留
├── data/              # ✅ 保留（但內容不上傳 Git）
├── docs/              # ✅ 保留
├── logs/              # ✅ 保留（但內容不上傳 Git）
├── strategies/        # ✅ 保留
├── tools/             # ✅ 保留
├── bot_main.py        # ✅ 保留
├── main.py            # ✅ 保留
└── README.md          # ✅ 已更新
```

## 清理步驟

### 1. 創建封存目錄
mkdir archived
mkdir archived/backtest_results
mkdir archived/deprecated_dashboards

### 2. 移動舊回測結果
mv *_results.txt archived/backtest_results/
mv temp_*.txt archived/backtest_results/
mv temp_*.csv archived/backtest_results/
mv result.txt archived/backtest_results/

### 3. 移動舊儀表板（可選）
# 如果確定不再使用
mv dashboard.py archived/deprecated_dashboards/
mv dashboard_realtime.py archived/deprecated_dashboards/

### 4. 更新 .gitignore
# 已包含，確認以下內容在 .gitignore 中
archived/
temp_*
*.tmp
