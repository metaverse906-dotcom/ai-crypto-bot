# 🎯 Adaptive DCA Bot 系統使用手冊

> **目的：讓 AI 助手快速了解整個系統，無需重複解釋**  
> 最後更新：2026-01-04

---

## 📋 快速摘要

### 系統目標
**透過 BTC + 山寨幣組合策略達到財務自由**

- **BTC 策略**：MVRV 加權動態 DCA（已部署運行）
- **山寨幣策略**：ADA 質押 + 動態 DCA（回測階段）
- **最終目標**：每月被動收入 $2,000 USD → 提早退休

### 當前狀態（2026-01-04）
| 項目 | 狀態 | 備註 |
|------|------|------|
| BTC DCA Bot | ✅ 運行中 | GCP 部署，週日 20:00 推送 |
| ADA 回測腳本 | ✅ 完成 | `comprehensive_altcoin_backtest.py` |
| Telegram Bot | ✅ 運行中 | 每週 DCA 建議 + 恐慌警報 |
| 投資記錄追蹤 | ❌ 未實作 | TODO 第一階段 |
| 多幣種支持 | ⚠️ 部分完成 | 僅 BTC，ADA 策略待整合 |

---

## 🏗️ 系統架構

### 核心組件

```
ai-crypto-bot/
├── 📡 Telegram Bot Layer (bot/)
│   ├── telegram_bot.py       # Bot 主程序
│   ├── scheduler.py           # 排程器（週日 20:00）
│   └── handlers/
│       ├── dca.py            # DCA 決策引擎
│       ├── mvrv_dca_analyzer.py  # MVRV 分析模組
│       └── menu.py           # 選單界面
│
├── 🧠 Strategy Layer (strategies/ & core/)
│   ├── strategies/hybrid_sfp.py      # SFP 策略（待完成，IP 限制）
│   ├── core/mvrv_data_source.py      # MVRV 數據源
│   ├── core/position_manager.py      # HIFO 倉位管理
│   └── core/risk_manager.py          # 風控模組
│
├── 📊 Configuration Layer (config/)
│   ├── dca_config.py          # DCA 參數（F&G 閾值、倍數）
│   ├── strategy_config.py     # 策略模式切換
│   └── symbols.py             # 幣種配置
│
├── 🔬 Backtest & Analysis (scripts/backtests/)
│   ├── comprehensive_altcoin_backtest.py  # ✅ 新增：山寨幣回測套件
│   ├── optimize_weights.py    # MVRV 權重優化
│   ├── mvrv_backtest.py       # BTC MVRV 回測
│   └── data/                  # 歷史數據 CSV
│
└── 🚀 Deployment
    ├── bot_main.py            # Bot 啟動入口
    ├── main.py                # SFP 系統入口（測試中）
    ├── docker-compose.yml     # Docker 配置
    └── .env                   # 環境變數
```

---

## 🎨 策略總覽

### 1. BTC 動態 DCA 策略（運行中）

#### 模式選擇
- **Fear & Greed 模式**（舊版）：基於市場情緒
- **MVRV 加權模式**（當前）：65% MVRV + 25% RSI + 10% F&G

#### 核心邏輯
```python
# 權重分數系統
綜合分數 = MVRV_Z_Score * 0.65 + RSI * 0.25 + F&G * 0.10

# 買入倍數
分數 < 15  → 3.5x 加碼（極度低估）
分數 < 25  → 2.0x 加碼
分數 < 35  → 1.5x 加碼
分數 < 50  → 1.0x 標準
分數 < 60  → 0.5x 減速
分數 ≥ 60  → 0.0x 停止
```

#### 倉位管理（HIFO）
- **核心倉 40%**：永不賣出
- **交易倉 60%**：週期獲利（Pi Cycle 交叉觸發）

#### 配置文件
- `.env`: `STRATEGY_MODE=MVRV` 或 `FG`
- `.env`: `BASE_WEEKLY_USD=250`
- `.env`: `MVRV_CORE_RATIO=0.4`

#### 回測績效（2020-2024）
| 策略 | 最終 BTC | vs HODL | 平均成本 |
|------|---------|---------|----------|
| HODL | 2.91 | - | $26,894 |
| **MVRV 加權** | **30.63** | **+952%** | **$24,353** |

---

### 2. ADA 山寨幣策略（開發中）

#### 為何選 ADA？
✅ **質押收益**：4-5% APY（Yoroi/Daedalus）  
✅ **流動性**：隨時解除委託  
✅ **週期性**：BTC.D 下降時表現優異

#### 動態 DCA 邏輯
```python
# 基於 BTC Dominance
BTC.D > 65%  → 3.0x 加碼（山寨超便宜）
BTC.D > 60%  → 2.5x
BTC.D > 55%  → 2.0x
BTC.D > 50%  → 1.5x
BTC.D > 45%  → 1.0x 標準
BTC.D > 40%  → 0.5x 減速
BTC.D < 40%  → 0.0x 停止（準備賣出）

# 賣出信號
Altseason Index > 75  → 全部賣出
持倉利潤 > 100%       → 賣出 50%（零成本持倉）
ETH/BTC > 0.08        → 賣出 50%
```

#### 回測結果（初步，2020-2026）
- **總報酬**：+143.69%
- **vs HODL**：-912.23%（問題：牛市停止買入錯過漲幅）
- **最大回撤**：-21.26%（vs HODL 70%+）

#### ⚠️ 待改進
1. **混合型 DCA**：60% 固定 + 40% 動態
2. **加入質押收益**：4.5% APY 複利計算
3. **優化賣出邏輯**：不要完全停止買入

---

## 🔧 技術細節

### 數據源

| 數據 | API | 降級方案 |
|------|-----|----------|
| MVRV Z-Score | Glassnode | 手動爬蟲 LookIntoBitcoin |
| Fear & Greed | Alternative.me | 快取（5 分鐘） |
| BTC 價格 | Binance/OKX/Bybit | 自動切換 |
| USD/TWD | ExchangeRate-API | 備用匯率 31.0 |
| BTC Dominance | CoinGecko | CSV 歷史數據 |

### 排程系統

```bash
# 週日 DCA 推送
每週日 20:00（台北時間） → Telegram 推送 DCA 建議

# 恐慌檢測（Cron）
每天 3 次（9:00, 15:00, 21:00）
→ 檢測 MVRV < 0.5 或 分數 < 20
→ 推送緊急買入機會

# Systemd 服務
sudo systemctl start crypto-bot
sudo systemctl enable crypto-bot
```

### 環境變數（.env）

```bash
# Telegram
TELEGRAM_BOT_TOKEN=你的token
TELEGRAM_ALLOWED_USERS=你的user_id

# 策略模式
STRATEGY_MODE=MVRV          # 或 FG
MVRV_CORE_RATIO=0.4         # 核心倉 40%
BASE_WEEKLY_USD=250         # 每週 $250

# API Keys（可選）
GLASSNODE_API_KEY=          # 留空使用降級
BINANCE_API_KEY=
BINANCE_SECRET=
```

---

## 📂 重要文件位置

### 配置與數據
```
data/positions.json         # 持倉追蹤（自動生成）
.env                        # 環境變數（敏感）
config/dca_config.py        # DCA 參數
config/strategy_config.py   # 策略模式
```

### 腳本與工具
```
bot_main.py                 # Telegram Bot 啟動
main.py                     # SFP 交易系統（測試）
run_panic_check.py          # 恐慌檢測（Cron 調用）
scripts/init_positions.py   # 初始化持倉
scripts/backtests/comprehensive_altcoin_backtest.py  # 山寨幣回測
```

### 文檔
```
README.md                   # 專案概覽
TODO.md                     # 功能待辦清單
CHANGELOG.md                # 更新歷史
docs/.gemini/               # 詳細文檔（部署、策略）
SYSTEM_MANUAL.md            # 本文件（系統手冊）
```

---

## 🚀 常用操作指令

### 本地開發
```bash
# 啟動 Telegram Bot
python bot_main.py

# 初始化持倉（首次使用）
python scripts/init_positions.py

# 回測 ADA 策略
python scripts/backtests/comprehensive_altcoin_backtest.py

# 檢查 MVRV 恐慌
python run_panic_check.py
```

### GCP 部署
```bash
# SSH 登入
ssh user@your-gcp-vm

# 查看 Bot 狀態
sudo systemctl status crypto-bot

# 查看日誌
sudo journalctl -u crypto-bot -f

# 重啟 Bot
sudo systemctl restart crypto-bot

# 手動備份
cp data/positions.json data/positions_backup_$(date +%Y%m%d).json
```

### Telegram Bot 指令
```
/start      - 開始使用
/dca_now    - 立即查看 DCA 建議
/menu       - 主選單
```

---

## 🎯 當前任務與優先級

### ✅ 已完成（2026-01-04）
1. BTC MVRV 加權策略部署
2. 週日自動 DCA 推送
3. 恐慌檢測系統
4. ADA 回測腳本（初版）

### 🔥 進行中
1. **整理系統文檔**（本文件）
2. **改進 ADA 策略**：
   - 加入質押收益計算
   - 混合型 DCA（60% 固定 + 40% 動態）
   - 重新回測驗證

### ⏳ 待辦（優先級排序）
1. **P0 - 核心功能**
   - [ ] 投資記錄追蹤（SQLite）
   - [ ] 視覺化報表（Matplotlib）
   - [ ] ADA 策略整合到 Telegram Bot

2. **P1 - 擴展功能**
   - [ ] 多幣種支持（ETH, SOL）
   - [ ] 財務自由計算器
   - [ ] 個人化設置（調整金額、通知時間）

3. **P2 - 優化改進**
   - [ ] SFP 策略實作（需解決 Binance IP 限制）
   - [ ] 數據備份到 Google Drive
   - [ ] 多用戶支持

詳見：`TODO.md`

---

## 💰 財務自由路徑規劃

### 目標
**每月被動收入 $2,000 USD**

### 方案 A：質押模式
- **所需資產**：$533,000（4.5% APY）
- **達成時間**：
  - 每週 $250 × 52 = $13,000/年
  - 考慮年化 30% 增值：**約 12-15 年**

### 方案 B：BTC + ADA 組合
- **配置**：BTC 70% + ADA 30%
- **質押收益**：ADA 部分 +4.5% APY
- **週期獲利**：山寨幣季節賣出獲利
- **達成時間**：**約 10-12 年**（需驗證）

### 下一步
1. 完成 ADA 改進回測
2. 計算組合策略的達標時間
3. 優化配置比例（BTC/ADA）

---

## 🔍 關鍵指標速查

### BTC MVRV 策略表現
- **回測期間**：2020-2024
- **vs HODL**：+952%
- **平均成本**：$24,353（vs HODL $26,894）

### ADA 策略表現（初步）
- **回測期間**：2020-2026
- **總報酬**：+143.69%
- **vs HODL**：-912.23%（需改進）
- **最大回撤**：-21.26%

### 系統運行狀態
- **部署平台**：Google Cloud e2-micro
- **運行時間**：24/7（自 2026-01-01）
- **週推送**：每週日 20:00
- **日檢測**：3 次（9:00, 15:00, 21:00）

---

## 🛡️ 安全與風控

### 手動執行原則
Bot **僅提供建議**，所有交易手動執行：
- ✅ 完全控制權
- ✅ 理解每筆交易
- ✅ 避免自動化風險

### 核心倉保護
- **40% 核心倉**：永不賣出
- 即使 Pi Cycle 交叉，核心倉保留
- 確保永遠持有 BTC

### 數據備份
```bash
# 每週備份
cp data/positions.json data/positions_backup_$(date +%Y%m%d).json

# 自動備份（計劃中）
# → Google Drive 每日備份
```

---

## 📞 常見問題

### Q1: 如何切換策略模式？
編輯 `.env`：
```bash
STRATEGY_MODE=MVRV  # 或 FG
```
重啟 Bot：
```bash
sudo systemctl restart crypto-bot
```

### Q2: 如何調整每週投入金額？
編輯 `.env`：
```bash
BASE_WEEKLY_USD=500  # 改為 $500
```

### Q3: 為什麼 ADA 回測表現不如 HODL？
**原因**：動態 DCA 在牛市中 BTC.D 低時停止買入，錯過漲幅。

**解決方案**：
1. 混合型 DCA（60% 固定 + 40% 動態）
2. 加入質押收益計算
3. 優化賣出邏輯

### Q4: 如何整合 ADA 到 Telegram Bot？
**待實作**（優先級 P0）：
1. 創建 `handlers/ada_dca.py`
2. 整合 BTC.D 數據源
3. 添加 `/dca_ada` 指令
4. 週日推送包含 ADA 建議

---

## 🎓 學習資源

### 策略文檔
- `docs/.gemini/STRATEGY_EXPLAINED.md` - 策略詳細原理
- `docs/.gemini/OPTIMAL_WEIGHTS.md` - 權重優化分析
- `docs/.gemini/MVRV_QUICKSTART.md` - MVRV 快速指南

### 部署文檔
- `docs/.gemini/DEPLOYMENT.md` - 完整部署流程
- `docs/.gemini/PRE_DEPLOYMENT_CHECKLIST.md` - 上線前檢查
- `docs/.gemini/BOT_OPERATIONS.md` - Bot 運作方式

---

## 🔄 版本歷史

| 版本 | 日期 | 更新內容 |
|------|------|----------|
| v1.1 | 2026-01-04 | 創建系統手冊、完成 ADA 回測腳本 |
| v1.0 | 2026-01-01 | MVRV 策略上線、GCP 部署 |
| v0.9 | 2025-12-30 | Fear & Greed Hybrid DCA |

---

## 📝 給 AI 助手的備註

### 對話延續指引
1. **開始新對話時**：先閱讀本文件（`SYSTEM_MANUAL.md`）
2. **了解當前狀態**：查看「當前任務與優先級」章節
3. **技術細節**：參考「系統架構」與「技術細節」
4. **數據位置**：查看「重要文件位置」

### 常見任務
- **回測相關**：使用 `scripts/backtests/` 資料
- **策略調整**：修改 `config/*.py`
- **Bot 功能**：編輯 `bot/handlers/*.py`
- **部署問題**：參考 `docs/.gemini/DEPLOYMENT.md`

### 關鍵事實
- ✅ BTC 策略已運行，MVRV 模式
- ⚠️ ADA 策略僅回測，未整合到 Bot
- ❌ SFP 策略受 Binance IP 限制阻塞
- 🎯 最終目標：每月 $2,000 被動收入

---

**最後更新**：2026-01-04  
**維護者**：使用者 + Antigravity AI
