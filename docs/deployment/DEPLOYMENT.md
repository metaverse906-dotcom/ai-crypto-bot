# 🚀 部署檢查清單

> F&G Hybrid DCA 策略完整部署指南

---

## ✅ 本地準備

### 1. 確認文件完整性
- [ ] `check_fg_panic.py` 已更新（$250 USD 基礎金額）
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

### 1. 創建 VM（首次部署）
- [ ] 已有 Google 帳號
- [ ] 已啟用 Google Cloud（$300 試用）
- [ ] 創建 VM（e2-micro, us-central1）

### 2. 連接到 VM
```bash
# SSH 連接
ssh your-username@your-vm-ip

# 進入項目目錄
cd /root/ai-crypto-bot
```

### 3. 拉取最新代碼
```bash
# 拉取 GitHub 更新
git pull origin main

# 確認文件存在
ls -la check_fg_panic.py
ls -la bot/handlers/dca.py
```

### 4. 配置 .env（VM 上）
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

### 5. 安裝依賴
```bash
# 安裝/更新依賴
pip3 install -r requirements.txt

# 確認關鍵包已安裝
pip3 list | grep -E "ccxt|requests|python-telegram-bot"
```

### 6. 設置 Cron 定時任務
```bash
# 編輯 crontab
crontab -e

# 添加以下行（每天早8點、下午2點、晚8點 UTC）:
0 0,6,12 * * * cd /root/ai-crypto-bot && /usr/bin/python3 check_fg_panic.py >> /var/log/fg_panic.log 2>&1

# 保存退出

# 確認設置
crontab -l
```

### 7. 設置 systemd 服務
```bash
# 創建服務文件
sudo nano /etc/systemd/system/crypto-bot.service

# 內容：
# [Unit]
# Description=AI Crypto Bot
# After=network.target
#
# [Service]
# Type=simple
# User=root
# WorkingDirectory=/root/ai-crypto-bot
# ExecStart=/usr/bin/python3 bot_main.py
# Restart=always
#
# [Install]
# WantedBy=multi-user.target

# 重新加載 systemd
sudo systemctl daemon-reload

# 啟動服務
sudo systemctl start crypto-bot

# 設置開機自啟動
sudo systemctl enable crypto-bot

# 檢查狀態
sudo systemctl status crypto-bot
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
$250 USD (1x) ≈ NT$7,750
```

### 2. 測試 Bot 服務
```bash
# 檢查服務狀態
sudo systemctl status crypto-bot

# 查看實時日誌
sudo journalctl -u crypto-bot -f
# （按 Ctrl+C 退出）

# Telegram 指令測試
/start  # 應 < 1 秒回應
/dca_now  # 應顯示當前分析
```

### 3. 檢查 Cron 日誌
```bash
# 查看恐慌檢測日誌
tail -20 /var/log/fg_panic.log

# 實時監控
tail -f /var/log/fg_panic.log
```

### 4. VM 重啟測試
```bash
# 重啟 VM
sudo reboot

# 重新連接後檢查
sudo systemctl status crypto-bot  # 應為 active (running)
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

### Bot 服務報錯

```bash
# 查看詳細日誌
sudo journalctl -u crypto-bot --no-pager -n 100

# 手動測試
cd /root/ai-crypto-bot
python3 bot_main.py

# 檢查依賴
pip3 list | grep -E "ccxt|telegram|python-dotenv"

# 重新安裝
pip3 install --upgrade -r requirements.txt
```

### 腳本報錯

```bash
# 手動執行查看錯誤
python3 check_fg_panic.py

# 檢查 Python 版本
python3 --version  # 應 >= 3.8

# 檢查路徑
which python3
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
- [ ] 依賴已安裝
- [ ] check_fg_panic.py 測試成功
- [ ] Cron 已設置（每天3次）
- [ ] systemd 服務已設置
- [ ] Bot 服務運行中
- [ ] /start 指令回應 < 1 秒
- [ ] /dca_now 指令測試成功
- [ ] Cron 日誌正常寫入
- [ ] VM 重啟後 Bot 自動啟動

**全部完成 = F&G Hybrid DCA 策略上線！** 🎉

---

## 📅 後續維護

### 每週檢查
```bash
# SSH 連接
ssh your-username@your-vm-ip

# 查看 Bot 日誌
sudo journalctl -u crypto-bot --since "1 week ago"

# 查看恐慌檢測日誌
tail -50 /var/log/fg_panic.log
```

### 每月檢查
- [ ] 檢查 VM 運行狀態
- [ ] 檢查 Bot 是否正常推送
- [ ] 檢查是否收到恐慌通知（如有出現）
- [ ] 檢查 API 額度使用
- [ ] 檢查磁盤空間（`df -h`）

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

# 驗證
sudo systemctl status crypto-bot
```

---

**準備開始部署！** 🚀
