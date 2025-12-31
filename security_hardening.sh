#!/bin/bash
# security_hardening.sh
# 系統安全加固腳本 - 部署前必須執行

echo "======================================"
echo "系統安全加固腳本"
echo "======================================"

# 1. 文件權限設置
echo ""
echo "1. 設置文件權限..."

if [ -f ".env" ]; then
    chmod 600 .env
    echo "✅ .env 權限設置為 600"
else
    echo "⚠️  .env 文件不存在，請從 .env.example 複製"
fi

if [ -f "secrets.json" ]; then
    chmod 600 secrets.json
    echo "✅ secrets.json 權限設置為 600"
else
    echo "⚠️  secrets.json 文件不存在，請從 secrets.json.example 複製"
fi

if [ -d "data" ]; then
    chmod 700 data
    echo "✅ data 目錄權限設置為 700"
fi

# 2. 檢查敏感文件是否在.gitignore中
echo ""
echo "2. 檢查 .gitignore 配置..."

check_gitignore() {
    if grep -q "$1" .gitignore; then
        echo "✅ $1 已在 .gitignore 中"
    else
        echo "❌ $1 未在 .gitignore 中！"
        return 1
    fi
}

check_gitignore ".env"
check_gitignore "secrets.json"
check_gitignore "data/"

# 3. 檢查是否有硬編碼的API密鑰
echo ""
echo "3. 檢查硬編碼的API密鑰..."

echo "檢查 Python 文件..."
if grep -r "BINANCE.*=" --include="*.py" . | grep -v "os.getenv" | grep -v "#" | grep -v "example"; then
    echo "❌ 發現可能的硬編碼 API 密鑰！"
else
    echo "✅ 未發現硬編碼 API 密鑰"
fi

# 4. Docker 安全檢查
echo ""
echo "4. 檢查 Docker 配置..."

if grep -q "restart: unless-stopped" docker-compose.yml; then
    echo "✅ Docker 自動重啟已配置"
fi

if grep -q "cpus:" docker-compose.yml; then
    echo "✅ CPU 限制已配置"
fi

if grep -q "memory:" docker-compose.yml; then
    echo "✅ 內存限制已配置"
fi

# 5. 生成安全建議文件
echo ""
echo "5. 生成安全建議..."

cat > SECURITY_CHECKLIST.md << EOF
# 部署前安全檢查清單

## ✅ 必須完成（部署前）

### Binance API 安全
- [ ] 登入 Binance -> API Management
- [ ] 創建新 API 密鑰（只允許現貨交易）
- [ ] **設置 IP 白名單**（只允許 VPS IP）
- [ ] **禁用提現權限**
- [ ] 設置 API 權限：只啟用「現貨交易」
- [ ] 複製 API Key 和 Secret 到 .env

### VPS 安全
- [ ] 使用 SSH 密鑰認證
- [ ] 禁用 SSH 密碼登入
- [ ] 配置防火牆（ufw）
  \`\`\`bash
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow 22/tcp
  sudo ufw allow 8501/tcp  # Streamlit (可選)
  sudo ufw enable
  \`\`\`
- [ ] 安裝 fail2ban
  \`\`\`bash
  sudo apt install fail2ban
  sudo systemctl enable fail2ban
  \`\`\`

### 文件安全
- [ ] 執行此腳本設置文件權限
- [ ] 確認 .env 和 secrets.json 不在 Git 中
- [ ] 設置 data/ 目錄權限為 700

### 環境變量
- [ ] 從 .env.example 複製到 .env
- [ ] 填入 Binance API 密鑰
- [ ] 填入 Telegram Bot Token (可選)
- [ ] 確認 .env 權限為 600

## 🔒 建議完成（部署後一週內）

### 監控
- [ ] 設置資源監控
- [ ] 配置錯誤告警
- [ ] 每日檢查日誌

### 備份
- [ ] 設置每日自動備份
- [ ] 測試備份恢復流程
- [ ] 備份到遠端存儲

### 更新
- [ ] 定期更新系統
  \`\`\`bash
  sudo apt update && sudo apt upgrade -y
  \`\`\`
- [ ] 定期更新 Docker 鏡像
  \`\`\`bash
  docker-compose pull
  docker-compose up -d
  \`\`\`

## 🎯 可選（提升安全性）

### 數據加密
- [ ] 加密 data/ 目錄
- [ ] 使用 Docker secrets

### 雙因素認證
- [ ] Telegram 操作確認
- [ ] 大額交易多重確認

### 審計
- [ ] 啟用審計日誌
- [ ] 定期檢視日誌

## ⚠️ 警告

### 絕對不要
- ❌ 將 .env 或 secrets.json 提交到 Git
- ❌ 在公共論壇分享 API 密鑰
- ❌ 使用有提現權限的 API
- ❌ 在未設置 IP 白名單前運行

### 立即停止運行如果
- 🚨 API 密鑰洩露
- 🚨 異常交易
- 🚨 系統被入侵
- 🚨 資源使用異常

## 📞 緊急應對

如果 API 密鑰洩露：
1. 立即登入 Binance 刪除 API 密鑰
2. 檢查是否有異常交易
3. 更換新的 API 密鑰
4. 檢查系統安全性
EOF

echo "✅ 已生成 SECURITY_CHECKLIST.md"

# 6. 檢查是否有 example 文件
echo ""
echo "6. 檢查配置文件..."

if [ -f ".env.example" ]; then
    echo "✅ .env.example 存在"
else
    echo "⚠️  建議創建 .env.example"
fi

if [ -f "secrets.json.example" ]; then
    echo "✅ secrets.json.example 存在"
else
    echo "⚠️  建議創建 secrets.json.example"
fi

# 7. 總結
echo ""
echo "======================================"
echo "安全加固完成"
echo "======================================"
echo ""
echo "✅ 已完成的項目："
echo "  - 文件權限設置"
echo "  - .gitignore 檢查"
echo "  - 硬編碼檢查"
echo "  - Docker 配置檢查"
echo "  - 生成安全檢查清單"
echo ""
echo "⚠️  請查看 SECURITY_CHECKLIST.md 完成部署前檢查"
echo ""
echo "🚀 部署前必須做："
echo "  1. 設置 Binance API IP 白名單"
echo "  2. 配置 VPS 防火牆"
echo "  3. 填寫 .env 文件"
echo "  4. 測試完整流程"
