# 🤖 AI Crypto Bot - F&G Hybrid DCA

智能加密貨幣 DCA（定期定額投資）機器人，採用 Fear & Greed 混合策略。

## 🎯 策略概述

**Fear & Greed Hybrid DCA** - 經過實際回測驗證的策略：
- 比普通 DCA 高 **30%** 績效
- 永不賣出，只買不賣
- 自動恐慌檢測，抓住極端機會

### 運作方式

**每週例行（主要）**：
- 時間：每週日晚上 8:00（台北時間）
- 檢查：Fear & Greed + RSI
- 通知：Telegram 建議買入金額
- 執行：手動分批買入

**緊急監控（輔助）**：
- 頻率：每天 3 次（早中晚）
- 觸發：F&G < 10 極度恐慌
- 通知：立即 Telegram 緊急通知
- 決定：你決定是否立即加碼

## 📊 買入倍數參考

| 市場狀況 | F&G | RSI | 倍數 |
|---------|-----|-----|------|
| 極度恐慌 | <10 | <25 | 4x |
| 強烈恐慌 | <20 | <30 | 3x |
| 市場恐慌 | <30 | - | 2x |
| RSI 恐慌 | - | <30 | 1.5x |
| 正常市場 | ≥30 | ≥30 | 1x |

*實際金額根據你的每週預算調整*

## 🚀 快速開始

### 1. 環境設置

```bash
# 克隆項目
git clone https://github.com/yourusername/ai-crypto-bot.git
cd ai-crypto-bot

# 安裝依賴
pip install -r requirements.txt

# 配置環境變數
cp .env.example .env
# 編輯 .env 填入你的 API keys
```

### 2. 調整買入金額

編輯 `bot/handlers/dca.py` 第61行：
```python
base_amount = 250  # 改成你的每週預算（USD）
```

編輯 `check_fg_panic.py` 同步調整。

### 3. Telegram Bot 設置

1. 與 [@BotFather](https://t.me/botfather) 對話創建 Bot
2. 獲取 Bot Token
3. 與 [@userinfobot](https://t.me/userinfobot) 對話獲取你的 User ID
4. 填入 `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_ALLOWED_USERS=your_user_id
   ```

### 4. 本地測試

```bash
# 測試 DCA 建議
python -c "from bot.handlers.dca import get_dca_analysis; import asyncio; print(asyncio.run(get_dca_analysis()))"

# 測試恐慌檢測
python scripts/analysis/check_fg_panic.py
```

### 5. 部署到 Google Cloud

詳見 [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md)

## 📁 專案結構

```
ai-crypto-bot/
├── 📁 bot/                  # Telegram Bot 核心
│   ├── handlers/            # 指令處理器
│   │   ├── dca.py          # DCA 建議邏輯（F&G Enhanced）
│   │   └── commands.py     # 基礎指令
│   ├── security/           # 安全驗證
│   └── scheduler.py        # 定時任務
├── 📁 core/                 # 核心邏輯
│   ├── brain.py            # 策略大腦
│   ├── database.py         # 數據存儲
│   ├── execution.py        # 交易執行
│   └── notifications.py    # 通知系統
├── 📁 strategies/           # 交易策略
│   ├── smart_dca_advisor.py # Smart DCA
│   └── hybrid_sfp.py       # SFP 混合策略
├── 📁 scripts/              # 工具腳本
│   ├── analysis/           # 市場分析
│   │   └── check_fg_panic.py  # 恐慌檢測
│   ├── backtests/          # 回測工具
│   ├── maintenance/        # 維護工具
│   ├── ai/                 # AI 工具
│   └── selectors/          # 幣種選擇器
├── 📁 docs/                 # 文檔
│   ├── deployment/         # 部署指南
│   └── strategy/           # 策略說明
├── 📁 config/               # 配置文件
├── 📁 data/                 # 數據存儲
├── 📁 logs/                 # 日誌文件
├── 📁 archive/              # 歸檔
├── 📄 main.py               # Bot 主程式
├── 📄 bot_main.py           # Bot 啟動入口
├── 📄 README.md             # 專案說明
├── 📄 TODO.md               # 待辦事項
└── 📄 CHANGELOG.md          # 更新日誌
```

## 🔧 主要指令

### Telegram Bot 指令

- `/start` - 開始使用
- `/dca_now` - 立即獲取 DCA 建議
- `/status` - 查看 Bot 狀態
- `/help` - 幫助訊息

### 系統管理（部署後）

```bash
# 重啟 Bot
sudo systemctl restart crypto-bot

# 查看日誌
sudo journalctl -u crypto-bot -f

# 查看恐慌檢測日誌
tail -f /var/log/fg_panic.log

# 檢查 Cron
crontab -l
```

## 📖 文檔

- **[DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md)** - Google Cloud 部署完整指南
- **[SECURITY_CHECKLIST.md](docs/deployment/SECURITY_CHECKLIST.md)** - 安全檢查清單
- **[SSH_SETUP_GUIDE.md](docs/deployment/SSH_SETUP_GUIDE.md)** - SSH 設置指南
- **[STRATEGY_EXPLAINED.md](docs/strategy/STRATEGY_EXPLAINED.md)** - 策略詳解
- **[scripts/README.md](scripts/README.md)** - 工具腳本使用說明

## ⚠️ 重要提醒

### 風險警告

- 加密貨幣投資有風險，可能損失全部本金
- 本 Bot 僅提供建議，不自動執行交易
- 所有買賣決定由你自己負責

### 安全建議

- ✅ 永遠不要分享 `.env` 文件
- ✅ 定期輪換 API keys
- ✅ 使用強密碼和 2FA
- ✅ 定期備份配置

### 資金管理

- 只投資你能承受損失的金額
- 建議投資比例：收入的 20-40%
- 保持 3-6 個月緊急預備金
- 建立加碼緩衝金

## 📈 回測績效

基於 2017-2024 歷史數據回測：

- **F&G Hybrid**: +691% ROI
- **普通 DCA**: +686% ROI
- **優勢**: +30% 累積 BTC

*過去績效不代表未來表現*

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

---

**免責聲明**: 本軟體僅供教育和研究目的。使用本軟體進行實際交易的風險由使用者自行承擔。
