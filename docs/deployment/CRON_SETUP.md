# Cron Jobs 配置說明

本文檔說明如何設置定時任務。

## 恐慌檢測（每天 3 次）

由於腳本已移至 `scripts/analysis/check_fg_panic.py`，我們提供了根目錄的入口腳本。

### Crontab 設定

```bash
# 編輯 crontab
crontab -e

# 添加以下行（每天早8點、下午2點、晚8點 UTC）
# 對應台北時間：下午4點、晚上10點、早上4點
0 0,6,12 * * * cd /home/benjamin_peng0408/ai-crypto-bot && /usr/bin/python3 run_panic_check.py >> /var/log/fg_panic.log 2>&1
```

### 手動測試

```bash
cd /home/benjamin_peng0408/ai-crypto-bot
python3 run_panic_check.py
```

### 查看日誌

```bash
# 查看最近 20 行
tail -20 /var/log/fg_panic.log

# 實時監控
tail -f /var/log/fg_panic.log
```

## 每週 DCA 建議

由 Bot 的 scheduler 自動處理：
- **時間**：每週日晚上 8:00（台北時間）
- **執行**：Bot 進程內的 APScheduler
- **無需 Cron**

## 健康檢查（未來可選）

```bash
# 每小時檢查 Bot 是否運行
0 * * * * systemctl is-active crypto-bot || systemctl restart crypto-bot
```
