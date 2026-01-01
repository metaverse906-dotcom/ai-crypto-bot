# 🚀 部署前最終檢查清單

## ✅ 本地準備

### 1. 確認文件完整性
- [ ] `check_fg_panic.py` 已更新（$280 基礎金額）
- [ ] `bot/handlers/dca.py` 已更新（F&G Enhanced）
- [ ] `.env` 文件存在且配置正確
- [ ] `.gitignore` 已更新（排除個資）

### 2. 測試本地運行
```bash
# 測試 DCA 建議
python -c "from bot.handlers.dca import get_dca_analysis; import asyncio; print(asyncio.run(get_dca_analysis()))"

# 測試恐慌檢測
python check_fg_panic.py

# 確認輸出正常
```

### 3. Git 提交
```bash
# 查看狀態（確認沒有個資）
git status

# 添加文件
git add .

# 提交
git commit -m "feat: F&G Hybrid DCA strategy with panic detection"

# 推送到 GitHub
git push origin main
```

---

## 🌩️ Google Cloud 部署

### 1. 連接到 VM
```bash
# SSH 連接
ssh your-username@your-vm-ip

# 進入項目目錄
cd /root/ai-crypto-bot
```

### 2. 拉取最新代碼
```bash
# 拉取 GitHub 更新
git pull origin main

# 確認文件存在
ls -la check_fg_panic.py
ls -la bot/handlers/dca.py
```

### 3. 配置 .env（VM 上）
```bash
# 創建 .env（如果不存在）
nano .env

# 填入（複製本地 .env 內容）：
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_ALLOWED_USERS=...
# OKX_API_KEY=...
# OKX_SECRET_KEY=...
# OKX_PASSPHRASE=...

# 保存：Ctrl+O, Enter, Ctrl+X
```

### 4. 安裝依賴
```bash
# 更新 requirements（如果需要）
pip3 install -r requirements.txt

# 確認 requests 已安裝
pip3 list | grep requests
```

### 5. 測試腳本
```bash
# 測試恐慌檢測
python3 check_fg_panic.py

# 應該看到：
# Fear & Greed: XX
# BTC Price: $XXX,XXX
# RSI(14): XX.X
# (可能有通知或 "No panic detected")
```

### 6. 設置 Cron 定時任務
```bash
# 編輯 crontab
crontab -e

# 添加以下行（每天早8點、下午2點、晚8點 UTC）:
0 0,6,12 * * * cd /root/ai-crypto-bot && /usr/bin/python3 check_fg_panic.py >> /var/log/fg_panic.log 2>&1

# 保存退出（按 Esc, 輸入 :wq, 按 Enter）

# 確認設置
crontab -l
```

### 7. 重啟 Bot 服務
```bash
# 重啟服務
sudo systemctl restart crypto-bot

# 檢查狀態
sudo systemctl status crypto-bot

# 查看日誌
sudo journalctl -u crypto-bot -f
# （按 Ctrl+C 退出）
```

---

## 🧪 驗證部署

### 1. 測試 Telegram 指令
在 Telegram 輸入：
```
/dca_now
```

**預期輸出**：
```
💰 Smart DCA 本週建議（F&G Enhanced）

🟢 正常市場 - 定期買入

市場狀態
BTC價格：$XXX,XXX
RSI(14)：XX.X
MA200：$XXX,XXX
Fear & Greed：XX (...)

分析
正常範圍 - 持續定投

本週建議
$280 (1x) ≈ NT$8,700
```

### 2. 檢查 Cron 日誌
```bash
# 查看恐慌檢測日誌
tail -20 /var/log/fg_panic.log

# 實時監控
tail -f /var/log/fg_panic.log
```

### 3. 等待下一次 Cron 執行
```bash
# 查看下次執行時間
# 早上8點（UTC 0:00）、下午2點（UTC 6:00）、晚上8點（UTC 12:00）

# 執行後檢查日誌
tail -f /var/log/fg_panic.log
```

---

## 📋 故障排除

### Cron 不執行

```bash
# 檢查 cron 服務
sudo systemctl status cron

# 如果未運行
sudo systemctl start cron
sudo systemctl enable cron

# 檢查系統日誌
grep CRON /var/log/syslog | tail -20
```

### 腳本報錯

```bash
# 手動執行查看錯誤
python3 check_fg_panic.py

# 檢查依賴
pip3 list | grep -E "ccxt|requests|python-telegram-bot"

# 重新安裝
pip3 install --upgrade ccxt requests python-telegram-bot python-dotenv
```

### Telegram 沒收到通知

```bash
# 檢查 .env 配置
cat .env | grep TELEGRAM

# 測試發送
python3 -c "
from telegram import Bot
import os
from dotenv import load_dotenv
load_dotenv()
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
bot.send_message(chat_id='YOUR_USER_ID', text='Test from VM')
"
```

---

## ✅ 部署完成確認

- [ ] Git 已推送（沒有個資）
- [ ] VM 代碼已更新
- [ ] .env 已配置
- [ ] check_fg_panic.py 測試成功
- [ ] Cron 已設置（每天3次）
- [ ] Bot 服務已重啟
- [ ] /dca_now 指令測試成功
- [ ] Cron 日誌正常寫入

**全部完成 = F&G Hybrid DCA 策略上線！** 🎉

---

## 📅 後續維護

### 每週檢查
```bash
# SSH 連接
ssh your-username@your-vm-ip

# 查看日誌
tail -50 /var/log/fg_panic.log
sudo journalctl -u crypto-bot --since "1 week ago"
```

### 每月檢查
- [ ] 檢查 VM 運行狀態
- [ ] 檢查 Bot 是否正常推送
- [ ] 檢查是否收到恐慌通知（如有出現）
- [ ] 檢查 API 額度使用

### 版本更新
```bash
# 本地修改後
git add .
git commit -m "update: ..."
git push

# VM 上拉取
cd /root/ai-crypto-bot
git pull
sudo systemctl restart crypto-bot
```

---

**準備開始部署！** 🚀
