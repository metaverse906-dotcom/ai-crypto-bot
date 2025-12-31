# 更新日誌

## [2024-12-31] 多幣種版本 + 動態市值選擇

### 新增功能
- ✅ 擴展幣種監控（5 → 13 個）
- ✅ 動態市值選擇器（CoinGecko API）
- ✅ 每週自動更新市值排名
- ✅ 支援多空雙向交易

### 配置變更
```python
# config/symbols.py
HYBRID_SFP_SYMBOLS = HYBRID_SFP_SYMBOLS_EXTENDED  # 13 個幣種

# config/symbols_extended.py
USE_DYNAMIC_SELECTION = True  # 啟用動態模式
DYNAMIC_TOP_N = 13            # 選擇前 13 名
```

### 預期改善
- 信號頻率：每週 2-3 個 → 7-10 個（增加 3倍）
- 年獲利：$2,285 → $2,880（+26%）
- 風險分散：5 幣種 → 13 幣種（跨越不同賽道）

### 技術細節
- 市值排名快取：7 天
- 排除穩定幣：USDT, USDC, BUSD, DAI
- API 來源：CoinGecko（免費）
- 更新頻率：每週一次（避免過度調整）

---

## [之前版本]
- Hybrid SFP 策略（4 小時時間框架）
- Smart DCA 提醒系統
- 多幣種監控（5 個核心幣種）
