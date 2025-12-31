# Smart DCA 策略設計文檔

## 核心問題分析

### 1. 買入週期：每日 vs 每週？

#### 每日買入
**優勢**：
- ✅ 更精確捕捉低點
- ✅ 平滑成本曲線
- ✅ 更符合"定期定額"概念

**劣勢**：
- ❌ 交易手續費高（365次/年）
- ❌ 管理複雜
- ❌ 小額買入效率低

#### 每週買入
**優勢**：
- ✅ 手續費合理（52次/年）
- ✅ 管理簡單
- ✅ 仍能抓住趨勢

**劣勢**：
- ⚠️ 可能錯過極短期低點

**建議：每週買入** ⭐

---

### 2. 賣出策略：關鍵考量

#### 傳統DCA問題
- 只買不賣 = 長期持有
- 適合強信仰者
- 但可能錯過獲利機會

#### Smart DCA 賣出邏輯

**目標**：
- 🎯 累積更多BTC（幣本位）
- 🎯 但在極度泡沫時保護利潤
- 🎯 賣出後在低點買回

**賣出條件（保守）**：
```python
# 同時滿足以下條件才賣出
1. RSI > 80（極度超買）
2. 價格 > MA200 + 50%（遠高於均線）
3. 近7日漲幅 > 30%（快速上漲）
```

**賣出比例**：
- 不是全賣
- 只賣 30-50%
- 保留核心倉位

**買回條件**：
```python
1. RSI < 40（回調）
2. 價格 < 賣出價 - 20%（顯著回落）
```

---

## Smart DCA 策略設計

### 版本 A：純買入（保守）

**適合**：長期信仰者

```python
每週日執行：
基礎金額 = $250/週

RSI調整：
- RSI < 30: 買入 $500（2x）
- RSI 30-40: 買入 $375（1.5x）
- RSI 40-70: 買入 $250（1x）
- RSI > 70: 買入 $125（0.5x）
- RSI > 80: 暫停買入

只買不賣，長期累積
```

**年投入**：$13,000（52週）
**目標**：累積最多BTC

---

### 版本 B：買低賣高（激進）⭐

**適合**：想優化報酬者

```python
每週日執行：

【買入邏輯】
基礎 = $250/週

RSI分級：
- RSI < 25: $500 + 動用儲備金
- RSI 25-35: $400
- RSI 35-45: $300
- RSI 45-65: $250
- RSI 65-75: $150
- RSI > 75: $50（象徵性）

【賣出邏輯】
觸發條件（三選一）：
1. RSI > 85 + 價格>MA200+60%
2. 單週漲幅 > 40%
3. 持續3週RSI>75且漲幅>50%

賣出策略：
- 計算總持倉BTC
- 賣出 40%（保留60%）
- 所得資金進入儲備池

【買回邏輯】
條件：
- RSI < 35
- 價格 < 上次賣出價 * 0.8
- 使用儲備金買入
```

**特點**：
- 低點多買
- 泡沫減倉
- 回調加倉
- 長期累積更多BTC

---

### 版本 C：雙池策略（平衡）

```python
資金分配：
- 60% 核心池：只買不賣
- 40% 交易池：買低賣高

核心池：
每週 $150，RSI調整買入
永不賣出

交易池：
每週 $100，RSI調整
允許在極端時賣出套利
目標：增加整體BTC數量
```

---

## 詳細回測方案

### 測試期間
- 2022全年（熊市）
- 2023全年（復甦）
- 2024全年（牛市）

### 對比策略
1. **普通DCA**：每週$250
2. **Smart DCA A**：RSI調整買入
3. **Smart DCA B**：買低賣高
4. **Smart DCA C**：雙池策略

### 評估指標
```python
1. 總投入金額
2. 累積BTC數量 ⭐（最重要）
3. 平均成本
4. 最終價值
5. 報酬率
6. 最大回撤
7. BTC買入賣出次數
8. 夏普比率
```

---

## 回測腳本設計

```python
class SmartDCA:
    def __init__(self, version='B'):
        self.version = version
        self.btc_holdings = 0
        self.total_invested = 0
        self.reserve_fund = 0
        self.trades = []
    
    def weekly_action(self, date, price, rsi, ma200):
        # 版本A：只買
        if self.version == 'A':
            amount = self.calculate_buy_amount(rsi)
            if amount > 0:
                self.buy(date, price, amount)
        
        # 版本B：買低賣高
        elif self.version == 'B':
            # 檢查賣出
            if self.should_sell(rsi, price, ma200):
                self.sell(date, price, ratio=0.4)
            
            # 買入
            amount = self.calculate_buy_amount(rsi)
            if amount > 0:
                self.buy(date, price, amount)
            
            # 檢查買回
            if self.should_buyback(rsi, price):
                self.buyback(date, price)
    
    def calculate_buy_amount(self, rsi):
        base = 250
        if rsi < 25: return base * 2 + self.reserve_fund * 0.1
        elif rsi < 35: return base * 1.6
        elif rsi < 45: return base * 1.2
        elif rsi < 65: return base
        elif rsi < 75: return base * 0.6
        else: return base * 0.2
```

---

## 我的推薦

### 建議策略：版本B（買低賣高）

**理由**：
1. **符合幣本位思維**
   - 主要目標：累積BTC
   - 但不死守"永不賣出"教條

2. **利用市場週期**
   - 熊市：積極買入
   - 牛市泡沫：部分獲利
   - 回調：再次買入

3. **實測優勢**（預期）
   - vs 普通DCA：+15-25% BTC數量
   - vs 純持有：+20-30%報酬

4. **風險可控**
   - 永遠保留60%核心倉
   - 只在極端時賣出
   - 有明確買回策略

---

## 下一步

1. **下載2022數據**
2. **實作回測腳本**
3. **測試三個版本**
4. **對比結果**
5. **選擇最優策略**

**預計時間**：1-2小時
