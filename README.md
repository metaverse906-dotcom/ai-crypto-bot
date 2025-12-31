# 🤖 AI Crypto Trading Bot

智能加密貨幣交易機器人，整合 Telegram Bot 控制、動態市值選擇和多策略交易系統。

## ✨ 核心功能

### 📊 交易策略
- **Hybrid SFP**：4小時時間框架，多空雙向交易
  - 年化報酬：+24%（回測 2023-2024）
  - Sharpe Ratio：0.80
  - 監控 13 個幣種（動態市值選擇）

- **Smart DCA**：每週建議系統
  - 基於 RSI 和 MA200 的智能定投
  - 手動執行，風險可控
  - 預期年獲利：$900-1,800

### 🤖 Telegram Bot
- 白名單認證系統
- 即時系統狀態查詢
- 遠端控制和監控
- 24/7 雲端運行

### 🎯 動態市值選擇
- 自動追蹤市值前 13 名幣種
- 每週更新一次
- CoinGecko API 整合
- 智能快取機制

## 🚀 快速開始

### 環境需求
- Python 3.8+
- Binance 帳號（API Key）
- Telegram Bot Token

### 安裝

```bash
# 克隆專案
git clone https://github.com/你的用戶名/ai-crypto-bot.git
cd ai-crypto-bot

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入你的 API Keys
```

### 配置 `.env`

```bash
# Binance API
BINANCE_API_KEY=你的_API_Key
BINANCE_SECRET=你的_Secret

# Telegram Bot
TELEGRAM_BOT_TOKEN=你的_Bot_Token
TELEGRAM_ALLOWED_USERS=你的_User_ID
TELEGRAM_ADMIN_USERS=你的_User_ID

# 其他設定
BOT_TIMEZONE=Asia/Taipei
USE_WEBHOOK=false
```

### 啟動 Bot

```bash
# 本地測試
python bot_main.py

# 或啟動完整系統
python main.py
```

## 📁 專案結構

```
ai-crypto-bot/
├── bot/                    # Telegram Bot
│   ├── config.py          # Bot 配置
│   ├── telegram_bot.py    # Bot 主程式
│   ├── handlers/          # 指令處理器
│   └── security/          # 認證模組
├── config/                # 系統配置
│   ├── symbols.py         # 幣種配置
│   └── symbols_extended.py # 動態市值選擇
├── strategies/            # 交易策略
│   ├── hybrid_sfp.py      # Hybrid SFP 策略
│   ├── smart_dca_advisor.py # Smart DCA
│   └── archived/          # 已封存策略
├── tools/                 # 工具腳本
│   ├── dynamic_market_cap_selector.py # 市值選擇器
│   └── backtest_*.py      # 回測工具
├── core/                  # 核心模組
│   ├── execution.py       # 交易執行
│   └── notifier.py        # 通知系統
├── bot_main.py           # Bot 啟動入口
├── main.py               # 系統主程式
└── requirements.txt      # 依賴清單
```

## ☁️ 部署到 Google Cloud

詳細步驟請參閱：[部署指南](DEPLOYMENT_CHECKLIST.md)

**快速部署**：
1. 創建 e2-micro VM（免費額度）
2. SSH 連接並克隆專案
3. 設定 `.env` 環境變數
4. 使用 systemd 自動啟動

**預期成本**：$0/月（免費額度內）

## 📊 效能數據

### Hybrid SFP 策略（2023-2024 回測）
- 總回報：+24.07%
- 勝率：31.47%
- 總交易：143 筆
- Sharpe Ratio：0.80

### Smart DCA（理論估算）
- 年投入：$13,000
- vs 普通 DCA：+15-25% BTC 數量
- 保守年獲利：$900-1,800

## 🔐 安全性

- ✅ `.env` 文件不追蹤（`.gitignore` 保護）
- ✅ Telegram 白名單認證
- ✅ API Key 隔離存儲
- ✅ Session 管理（30 分鐘超時）
- ✅ Rate limiting 防濫用

## 📝 待辦事項與優化建議

### 🔄 待完成功能
- [ ] 恢復動態市值選擇（目前為靜態列表）
- [ ] 實作 `/dca_now` 指令（Smart DCA 建議）
- [ ] 實作 `/positions` 指令（倉位查詢）
- [ ] 實作 `/market` 指令（市場數據）
- [ ] 添加圖表生成功能

### ⚡ 效能優化建議
- [ ] 升級 VM 到 e2-small（如需更快回應）
- [ ] 實作 Redis 快取（減少 API 請求）
- [ ] 使用 Webhook 替代 Polling（降低延遲）

### 🔐 安全性增強
- [ ] 實作 Rate Limiting
- [ ] 加入更嚴格的權限控制
- [ ] 設定 Binance API IP 白名單自動更新

### 📊 數據分析
- [ ] 添加交易績效統計
- [ ] 實作 Dashboard 可視化
- [ ] 交易日誌自動備份

> 💡 **提示**：系統穩定運行後，可以逐步實作這些功能

---

## 📈 更新日誌

### [2024-12-31] 最新版本
- ✅ Telegram Bot 完整實作
- ✅ 動態市值選擇器（每週更新）
- ✅ 效能優化（延遲載入、快取機制）
- ✅ 多幣種支援（5 → 13 個）
- ✅ Google Cloud 部署支援

### 已封存功能
- Silver Bullet 策略（-22.59% 虧損，已棄用）

## 🛠️ 開發

### 執行測試
```bash
python tools/backtest_*.py
```

### 更新代碼
```bash
git pull
pip install -r requirements.txt
sudo systemctl restart crypto-bot  # 如果在雲端
```

## 📝 授權

本專案僅供個人學習使用。

## ⚠️ 免責聲明

- 加密貨幣交易具有高風險
- 回測結果不保證未來表現
- 請謹慎投資，風險自負
- 建議先用小資金測試

## 🤝 貢獻

本專案為個人專案，暫不開放貢獻。

## 📧 聯繫

如有問題，請透過 GitHub Issues 回報。

---

**⭐ 如果這個專案對你有幫助，請給個 Star！**
