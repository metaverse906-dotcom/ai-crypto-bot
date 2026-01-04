# 🤖 Adaptive DCA Bot（自適應 DCA 機器人）

智能加密貨幣定投助手 - 使用 MVRV Z-Score 加權策略優化 BTC 累積

## 🎯 核心功能

### 動態 DCA 策略

**MVRV 加權分數系統 + 動能賣出**（回測 2020-2025）：
- vs HODL：雖輸約 31.8%（DCA 在牛市的結構性劣勢）
- vs 原系統：改善 +1.7%（學術級動能最優化）
- 風險管理：自動分批退出，降低回調損失
- **MVRV Z-Score 65%** - 鏈上估值主導（改進線性插值，誤差 0.55）
- **RSI 25%** - 技術面確認
- **Fear & Greed 10%** - 情緒輔助

**智能交易所切換**：自動偵測 Binance/OKX/Bybit 可用性

**智能倍數調整**：
- 極度低估（分數<15）：3.5x 加碼
- 強力低估（分數<25）：2.0x 加碼
- 低估區間（分數<35）：1.5x 加碼
- 正常區間（分數<50）：1.0x 標準
- 輕度高估（分數<60）：0.5x 減速
- 過熱區域（分數≥60）：0.0x 停止

### 🛡️ 安全機制與賣出策略

**學術級 MVRV 動能賣出**（經 2020-2025 回測優化）：

基於 MVRV Z-Score 動能變化的三階段自適應退出：

**階段 1 - 快速上升期**（Rapid Ascent）:
- 檢測：斜率 > 0.05（14日EMA平滑，7日線性回歸）
- 策略：微量賣出（0.2% × 0.5 × intensity）
- 目的：保持倉位，讓利潤奔跑

**階段 2 - 高原期**（Plateau - 關鍵賣出區）:
- 檢測：斜率在 ±0.03，且 MVRV > 3.0
- 策略：主力賣出（1.0% × 2.5 × intensity）
- 目的：動能耗盡時分批退出

**階段 3 - 下跌期**（Decline）:
- 檢測：斜率 < -0.05
- 策略：加速賣出（1.0% × 4.0 × intensity）
- 目的：趨勢反轉時快速離場

**備用觸發**（保險機制）：
- **Pi Cycle Top 交叉** → 清空交易倉
- **月線 RSI > 85** → 停止買入

### HIFO 倉位管理

**核心倉/交易倉分離**（40/60）：
- **核心倉 40%**：永不賣出，長期持有
- **交易倉 60%**：動態管理，週期獲利

**HIFO 賣出**：優先賣出高成本幣，降低平均成本

## 🔬 技術實現

### MVRV 動能分析器

**核心技術**：
- **14 日 EMA 平滑**：消除 MVRV Z-Score 短期噪音
- **7 日線性回歸**：計算斜率，檢測動能變化
- **動態 DCA Out 公式**：`Sell% = Base_Rate × Momentum_Factor × (SZ / 2.0)`

**參數設置**（經研究論文優化）：
```
啟動閾值：MVRV > 1.5（適應新市場環境）
高位閾值：MVRV > 3.0（vs 歷史 7.0）
斜率閾值：±0.03（高原）, +0.05（上升）, -0.05（下跌）
```

**依賴套件**：
- `scipy`：線性回歸計算
- `numpy`：數值運算
- `pandas`：數據處理

## 📅 自動化排程

### 每週提醒
- **時間**：每週日 20:00（台北時間）
- **內容**：DCA 建議 + 市場分析
- **方式**：Telegram 自動推送

### 即時警報
- **頻率**：每天 3 次（9:00, 15:00, 21:00）
- **觸發**：
  - MVRV < 0.5（極度低估）
  - 綜合分數 < 20（極端機會）
  - Pi Cycle 交叉（頂部警告）

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 配置環境

複製 `.env.example` 到 `.env`：

```bash
# Telegram
TELEGRAM_BOT_TOKEN=你的token
TELEGRAM_ALLOWED_USERS=你的user_id

# 策略配置
STRATEGY_MODE=MVRV
MVRV_CORE_RATIO=0.4
BASE_WEEKLY_USD=250

# 可選
GLASSNODE_API_KEY=  # 留空使用降級方案
```

### 3. 初始化持倉

如有現有 BTC，修改 `scripts/init_positions.py`：

```python
EXISTING_BTC = 0.21
ESTIMATED_COST = 50000  # 你的實際平均成本
```

執行初始化：

```bash
python scripts/init_positions.py
```

### 4. 啟動 Bot

```bash
python main.py
```

### 5. Telegram 指令

```
/start - 開始使用
/dca_now - 立即查看 DCA 建議
```

## 📊 策略效果（回測 2020-2024）

| 策略 | 最終 BTC | vs HODL | 平均成本 |
|------|---------|---------|---------|
| HODL | 2.91 | - | $26,894 |
| 純 MVRV | 14.30 | +391% | $21,699 |
| MVRV+RSI 確認 | 23.97 | +724% | $21,108 |
| **加權分數（65/25/10）** | **30.63** | **+952%** | **$24,353** |

## 🗂️ 專案結構

```
ai-crypto-bot/
├── bot/
│   ├── handlers/
│   │   ├── dca.py              # DCA 處理器（多模式）
│   │   └── mvrv_dca_analyzer.py # MVRV 分析模組
│   └── scheduler.py            # 自動排程
├── core/
│   ├── mvrv_data_source.py     # MVRV 數據源
│   ├── position_manager.py     # HIFO 倉位管理
│   └── signal_notifier.py      # Telegram 通知
├── scripts/
│   ├── analysis/
│   │   └── check_mvrv_panic.py # 極端機會偵測
│   ├── backtests/
│   │   └── optimize_weights.py # 權重優化測試
│   └── init_positions.py       # 持倉初始化
├── config/
│   └── strategy_config.py      # 策略配置
└── data/
    └── positions.json          # 持倉追蹤（自動生成）
```

## 🔧 部署到 GCP

詳見：
- [部署指南](docs/.gemini/DEPLOYMENT.md)
- [部署前檢查](docs/.gemini/PRE_DEPLOYMENT_CHECKLIST.md)

### 簡要步驟

1. **上傳代碼**
```bash
scp -r ai-crypto-bot user@gcp-vm:/home/user/
```

2. **安裝依賴**
```bash
ssh user@gcp-vm
cd ai-crypto-bot
pip install -r requirements.txt
```

3. **配置環境**
```bash
cp .env.example .env
nano .env  # 設定 token
```

4. **設定 Systemd**
```bash
sudo nano /etc/systemd/system/crypto-bot.service
sudo systemctl enable crypto-bot
sudo systemctl start crypto-bot
```

5. **設定 Crontab**（極端警報）
```bash
crontab -e
# 添加：
0 9,15,21 * * * cd /path/to/bot && python3 run_panic_check.py
```

## 📖 詳細文檔

### 策略相關
- [策略完整說明](docs/.gemini/STRATEGY_EXPLAINED.md) - 詳細運作原理
- [權重優化分析](docs/.gemini/OPTIMAL_WEIGHTS.md) - 為何 65/25/10
- [MVRV 快速指南](docs/.gemini/MVRV_QUICKSTART.md) - 啟用 MVRV 模式

### 部署相關
- [最終配置](docs/.gemini/FINAL_SETUP.md) - 配置摘要
- [部署指南](docs/.gemini/DEPLOYMENT.md) - 完整部署流程
- [運作方式](docs/.gemini/BOT_OPERATIONS.md) - Bot 如何運作
- [部署檢查](docs/.gemini/PRE_DEPLOYMENT_CHECKLIST.md) - 上線前必做

## ⚙️ 配置說明

### 策略模式

在 `.env` 中設定：

```bash
STRATEGY_MODE=MVRV   # MVRV 加權策略（推薦）
# STRATEGY_MODE=FG   # Fear & Greed 模式（舊版）
```

### 核心倉比例

```bash
MVRV_CORE_RATIO=0.4  # 40% 核心倉（平衡）
# 0.5 = 保守（50% 永不賣）
# 0.3 = 激進（30% 核心，70% 交易）
```

### 每週投入

```bash
BASE_WEEKLY_USD=250  # 每週基準投入 $250
```

## 🚨 重要提醒
## 📂 專案結構

```
ai-crypto-bot/
├── bot/                    # Telegram Bot 主程式
├── core/                   # 核心模組
│   ├── mvrv_data_source.py         # MVRV 數據源
│   ├── mvrv_momentum_analyzer.py   # 學術級動能分析器 ⭐
│   ├── position_manager.py         # HIFO 倉位管理
│   └── exchange_manager.py         # 交易所管理
├── config/                 # 配置文件
├── scripts/                # 工具腳本
│   ├── init_positions.py           # 初始化倉位
│   └── backtests/                  # 回測腳本（開發用）
├── archive/                # 封存的研究文件 📦
│   ├── research_backtests/         # 歷史回測腳本
│   └── temp_results/               # 回測結果文本
├── requirements.txt        # Python 依賴
├── README.md              # 本文檔
└── ARCHIVE_INFO.md        # 封存說明

⭐ = 最新整合的學術級功能
📦 = 不部署到生產環境（已由 .gitignore 排除）
```

## 📦 封存文件說明

`archive/` 資料夾包含研究過程與回測腳本，已由 `.gitignore` 排除，不會部署。

**封存內容**：
- 6+ 種賣出策略的回測腳本
- 歷史回測結果與分析
- 研究過程文檔

**查看詳情**：請參閱 [`ARCHIVE_INFO.md`](./ARCHIVE_INFO.md)

## 🚀 部署前檢查

部署到 GCP 前請確認：
- [x] 動能分析器已整合（監控模式）
- [x] README 已更新
- [x] 不必要的文件已封存
- [ ] scipy 依賴已加入 requirements.txt
- [ ] 本地測試 Bot 運行正常
- [ ] .env 配置正確
- [ ] secrets.json 已設置

---

**版本**：v2.0 Academic Momentum Edition
**最後更新**：2026-01-04

### 手動執行
Bot 只提供建議，**所有交易需手動執行**：
- 收到建議後自行到交易所操作
- 確保完全控制權
- 理解每筆交易的邏輯

### 數據備份
定期備份 `data/positions.json`：
```bash
cp data/positions.json data/positions_backup_$(date +%Y%m%d).json
```

### 核心倉保護
- 核心倉**永不賣出**
- 即使 Pi Cycle 交叉，核心倉仍保留
- 確保永遠持有 BTC

## 📈 使用建議

### 適合人群
- ✅ 長期看好 BTC
- ✅ 願意定期投入
- ✅ 理解週期規律
- ✅ 能接受波動

### 不適合
- ❌ 追求短期暴利
- ❌ 無法承受虧損
- ❌ 頻繁進出交易
- ❌ 完全不懂技術

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

## ⚠️ 免責聲明

本工具僅供學習和參考，不構成投資建議。加密貨幣投資有風險，請謹慎決策。
