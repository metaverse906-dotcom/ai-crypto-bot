# 🤖 Adaptive DCA Bot - AI 助手速查表

> **給 Antigravity 或其他 AI 助手的快速參考**  
> 閱讀時間：< 2 分鐘

---

## 🎯 核心事實（30 秒速覽）

### 系統目標
**財務自由路徑**：BTC + ADA 組合 → 每月 $2,000 被動收入

### 當前狀態（2026-01-04 v2.0）
- ✅ **BTC MVRV 策略**：運行中（GCP），週日 20:00 推送
- ✅ **學術級動能分析**：已整合（監控模式），Telegram 顯示
- ✅ **檔案整理**：研究文件已封存到 `archive/`
- ✅ **文檔更新**：README, ARCHIVE_INFO, 部署檢查清單完成
- 🔄 **待本地測試**：動能分析器運行驗證
- ❌ **投資追蹤**：未實作
- ❌ **ADA Bot 整合**：未實作（研究已封存）

### 立即參考
- 完整文檔：`SYSTEM_MANUAL.md`
- 專案概覽：`README.md`
- 待辦清單：`TODO.md`

---

## 📂 關鍵文件定位

### 啟動腳本
```bash
bot_main.py                 # Telegram Bot（BTC DCA）
main.py                     # SFP 交易系統（測試中，IP 限制）
run_panic_check.py          # 恐慌檢測（Cron）
```

### 策略配置
```bash
.env                        # STRATEGY_MODE, BASE_WEEKLY_USD
config/strategy_config.py   # 策略模式類
config/dca_config.py        # F&G/MVRV 參數
```

### 回測工具
```bash
scripts/backtests/comprehensive_altcoin_backtest.py  # ADA 回測（新）
scripts/backtests/mvrv_backtest.py                   # BTC MVRV 回測
scripts/backtests/optimize_weights.py                # 權重優化
```

### Bot 處理器
```bash
bot/handlers/dca.py                 # BTC DCA 邏輯
bot/handlers/mvrv_dca_analyzer.py   # MVRV 分析 + 動能監控 ⭐
bot/handlers/menu.py                # 選單界面
```

### 核心模組
```bash
core/mvrv_data_source.py            # MVRV 數據源
core/mvrv_momentum_analyzer.py      # 學術級動能分析器 ⭐ 新增
core/position_manager.py            # HIFO 倉位管理
core/exchange_manager.py            # 交易所管理
```

### 封存文件
```bash
archive/research_backtests/         # 歷史回測腳本（不上傳）
archive/temp_results/               # 回測結果（不上傳）
ARCHIVE_INFO.md                     # 封存說明文檔
```

---

## 🔥 常見任務速查

### 任務 1：回測 ADA 策略
```bash
cd d:\使用者\Desktop\ai-crypto-bot
python scripts/backtests/comprehensive_altcoin_backtest.py
# 輸出：scripts/backtests/reports/*.txt, *.png
```

### 任務 2：修改 BTC DCA 參數
```bash
# 編輯 .env
STRATEGY_MODE=MVRV
BASE_WEEKLY_USD=500
MVRV_CORE_RATIO=0.4

# 或直接改 config/dca_config.py
```

### 任務 3：部署到 GCP
```bash
# 1. 上傳
scp -r ai-crypto-bot user@gcp:/home/user/

# 2. SSH 進入
ssh user@gcp

# 3. 重啟服務
sudo systemctl restart crypto-bot
sudo journalctl -u crypto-bot -f  # 查看日誌
```

### 任務 4：查看回測結果
```bash
# BTC MVRV 回測
python scripts/backtests/mvrv_backtest.py

# ADA 回測（含圖表）
python scripts/backtests/comprehensive_altcoin_backtest.py
```

---

## 🎨 策略速查

### BTC 加權分數 + 學術級動能策略 ⭐
```
買入策略（加權分數）:
綜合分數 = MVRV * 0.65 + RSI * 0.25 + F&G * 0.10

分數 < 15  → 3.5x
分數 < 25  → 2.0x
分數 < 50  → 1.0x
分數 ≥ 60  → 0.0x（停止）

倉位：40% 核心（永不賣）+ 60% 交易（動態賣出）

賣出策略（MVRV 動能 - v2.0 監控模式）:
- 14 日 EMA 平滑 MVRV Z-Score
- 7 日線性回歸計算斜率

階段 1 (快速上升): 斜率 > 0.05
  → 微量賣出 0.2% × 0.5 × intensity
  
階段 2 (高原期): 斜率在 ±0.03, MVRV > 3.0 【關鍵賣出區】
  → 主力賣出 1.0% × 2.5 × intensity
  
階段 3 (下跌期): 斜率 < -0.05
  → 加速賣出 1.0% × 4.0 × intensity

當前：監控模式（僅顯示，不自動執行）
```

---

## ⚠️ 已知問題 & 決策

| 問題 | 狀態 | 結論/解法 |
|------|------|----------|
| DCA vs HODL 表現 | � 已研究 | DCA 在持續牛市（2020-2025）結構性輸 HODL 30%，這是 DCA 本質，**已接受** |
| 賣出策略優化 | 🟢 已完成 | 測試 6+ 種策略，學術級動能最佳（+1.7% vs 原系統），**已採用** |
| ADA 策略表現 | � 已封存 | 回測低於 HODL，**暫緩整合**，研究文件已封存至 `archive/` |
| Binance API IP 限制 | � 已知 | 暫時無解，等待或使用 VPN |

---

## 🚀 優先級（下一步做什麼）

### P0 - 立即執行（v2.0 部署）
1. ✅ 整合學術級動能策略（已完成）
2. ✅ 整理封存文件（已完成）
3. ✅ 更新文檔（已完成）
4. 🔄 **本地測試 Bot 運行**
5. 🔄 **上傳 Git 並部署到 GCP**

### P1 - 短期監控（1-2 週）
1. 觀察動能分析信號
2. 驗證三階段檢測邏輯
3. 記錄賣出建議時機
4. 評估是否啟用自動賣出

### P2 - 長期優化（暫緩）
- 投資記錄追蹤
- 視覺化報表
- ADA 策略（已封存）

---

## 🛠️ 技術棧

```
語言：Python 3.12
Bot：python-telegram-bot 21.0
數據：pandas, numpy, matplotlib
回測：vectorbt（進階功能）
部署：GCP e2-micro, Systemd, Cron
數據源：Glassnode(MVRV), Alternative.me(F&G), Binance(價格)
```

---

## 💡 AI 助手使用指引

### 對話開始時
1. 先讀 `SYSTEM_MANUAL.md`（詳細版）
2. 或讀本文件（快速版）
3. 了解「當前任務」章節

### 回答問題時
- 參考「策略速查」
- 查看「關鍵文件定位」
- 引用 `TODO.md` 的優先級

### 編寫代碼時
- 遵循現有風格（參考 `core/`, `bot/handlers/`）
- 配置寫在 `config/*.py`
- 回測腳本放 `scripts/backtests/`

### 部署相關
- 參考 `docs/.gemini/DEPLOYMENT.md`
- 環境變數在 `.env`
- Systemd 服務：`crypto-bot.service`

---

## 📞 使用者偏好

### 代碼風格
- ✅ 直接給代碼，不要「這是如何做」
- ✅ 保持簡潔，不要冗長解釋
- ✅ 繁體中文回覆
- ✅ 預測需求，主動建議

### 溝通方式
- ❌ 不要道德說教
- ❌ 不要重複全部代碼
- ✅ 給修改前後幾行即可
- ✅ 直接給答案，後續再解釋

---

**快速連結**：
- 詳細手冊：`SYSTEM_MANUAL.md`
- 專案說明：`README.md`
- 功能待辦：`TODO.md`
- 封存說明：`ARCHIVE_INFO.md` ⭐
- 部署檢查：查看 Antigravity artifacts `deployment_checklist.md` ⭐

**版本**：v2.0 Academic Momentum Edition  
**最後更新**：2026-01-04  
**重大變更**：整合學術級 MVRV 動能分析器（監控模式）

