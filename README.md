# 🤖 AI Crypto DCA Bot

智能加密貨幣定投助手 - 使用 MVRV Z-Score 加權策略優化 BTC 累積

## 🎯 核心功能

### 動態 DCA 策略

**MVRV 加權分數系統**（回測 +82.7% vs HODL）：
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

### 安全機制

**強制覆蓋系統**：
- **Pi Cycle Top 交叉** → 立即停止買入 + 清空交易倉
- **月線 RSI > 85** → 否決買入（即使估值低）

### HIFO 倉位管理

**核心倉/交易倉分離**（40/60）：
- **核心倉 40%**：永不賣出，長期持有
- **交易倉 60%**：動態管理，週期獲利

**HIFO 賣出**：優先賣出高成本幣，降低平均成本

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
