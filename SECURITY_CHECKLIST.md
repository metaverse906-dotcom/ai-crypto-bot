# 部署安全檢查清單

## ⚠️ 部署前必須完成

### 1. Binance API 安全設置 ⭐

**登入 Binance → API Management**

1. 創建新的 API 密鑰
2. **設置 IP 白名單**
   ```
   只允許你的 VPS IP 訪問
   例如：123.45.67.89
   ```
3. **設置 API 權限**
   - ✅ 啟用：現貨交易
   - ❌ 禁用：提現
   - ❌ 禁用：萬向轉帳
   - ❌ 禁用：合約交易（如果不需要）
4. 複製 API Key 和 Secret 到 .env

**為什麼這很重要？**
- IP 白名單：即使 API 密鑰洩露，駭客也無法使用
- 禁用提現：防止資金被盜

---

### 2. 環境變量設置

**複製範例文件**：
```bash
cp .env.example .env
cp secrets.json.example secrets.json
```

**填寫 .env**：
```bash
# Binance API（必須）
BINANCE_API_KEY=你的API密鑰
BINANCE_SECRET=你的Secret

# Telegram（可選，用於通知）
TELEGRAM_BOT_TOKEN=你的Bot Token
TELEGRAM_CHAT_ID=你的Chat ID

# Gemini AI（可選）
GEMINI_API_KEY=你的Gemini密鑰
```

**設置文件權限**（Linux/Mac）：
```bash
chmod 600 .env
chmod 600 secrets.json
chmod 700 data/
```

**Windows**：
右鍵 .env → 屬性 → 安全性 → 只允許你的用戶讀取

---

### 3. VPS 安全加固（如果使用Linux VPS）

**SSH 安全**：
```bash
# 禁用密碼登入（使用密鑰）
sudo nano /etc/ssh/sshd_config
# 設置：PasswordAuthentication no
sudo systemctl restart sshd
```

**防火牆設置**：
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp          # SSH
sudo ufw allow 8501/tcp         # Streamlit（可選）
sudo ufw enable
```

**安裝 fail2ban**：
```bash
sudo apt update
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

---

## ✅ 部署後檢查

### 1. 測試系統

**測試 Docker**：
```bash
docker-compose up -d
docker-compose logs -f
```

**檢查服務**：
```bash
docker ps
# 應該看到所有容器都在運行
```

### 2. 監控前 24 小時

**每 4 小時檢查**：
- 查看 Docker 日誌
- 檢查系統資源
- 確認沒有錯誤

**使用指令**：
```bash
# 查看日誌
docker-compose logs --tail=100

# 查看資源使用
docker stats

# 查看磁盤空間
df -h
```

---

## 🚨 安全警告

### 絕對不要做

- ❌ 將 .env 或 secrets.json 提交到 Git
- ❌ 在公共場合分享 API 密鑰
- ❌ 使用有提現權限的 API
- ❌ 在不安全的網絡上傳輸密鑰
- ❌ 在未設置 IP 白名單前運行

### 立即停止如果

- 🚨 發現異常交易
- 🚨 API 密鑰可能洩露
- 🚨 系統資源異常
- 🚨 收到不明登入通知

---

## 📞 緊急應對計劃

### API 密鑰洩露

1. **立即**登入 Binance 刪除 API 密鑰
2. 檢查交易歷史是否有異常
3. 停止 Docker 容器：`docker-compose down`
4. 生成新的 API 密鑰
5. 檢查系統安全性

### 異常交易

1. 立即停止系統：`docker-compose down`
2. 查看交易歷史
3. 查看系統日誌：`tail -100 logs/*.log`
4. 聯繫技術支持

---

## 📋 每日/每週檢查

### 每日
- [ ] 查看 Docker 日誌
- [ ] 檢查交易記錄
- [ ] 確認策略正常運行

### 每週
- [ ] 備份 data/ 目錄
- [ ] 更新系統
- [ ] 檢查磁盤空間

### 每月
- [ ] 更新 Docker 鏡像
- [ ] 檢查依賴更新
- [ ] 審計交易歷史

---

## 總結

**最關鍵的 3 件事**：

1. ⭐ **Binance API IP 白名單** - 最重要的安全措施
2. ⭐ **禁用提現權限** - 防止資金被盜
3. ⭐ **文件權限 600** - 防止其他用戶讀取

**完成這 3 項後，系統基本安全可用** ✅
