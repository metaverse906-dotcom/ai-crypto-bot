# core/brain.py
import google.generativeai as genai
import json
import os
import asyncio
import pandas as pd
import pandas_ta as ta

class TradingBrain:
    def __init__(self):
        self._init_api()
        
        # 動態發現並配置模型參謀團
        self.model_map = self._discover_best_models()
        self.models = {}
        
        # 初始化三個等級的模型
        for tier, model_id in self.model_map.items():
            print(f"🧠 初始化 AI 參謀 [{tier}]: {model_id}")
            self.models[tier] = genai.GenerativeModel(
                model_name=model_id,
                generation_config={"response_mime_type": "application/json"}
            )

    def _discover_best_models(self):
        """
        自動搜尋目前 API 可用的 Gemeni 模型 (Text-out / Generate Content)。
        嚴格過濾：
        1. 必須支援 `generateContent`。
        2. 名稱必須包含 `gemini`。
        3. 排除 `nano` (太小) 和 `bison` (舊版)。
        """
        print("🔍 正在掃描 Google Gemini 模型庫 (過濾 nano/legacy)...")
        
        fallback_map = {
            "LITE": "gemini-2.0-flash-lite-preview-02-05", 
            "FLASH": "gemini-2.0-flash",
            "PRO": "gemini-1.5-pro"
        }
        
        try:
            all_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    name = m.name.replace('models/', '')
                    # 嚴格過濾
                    if 'gemini' not in name: continue
                    if 'nano' in name: continue
                    
                    all_models.append(name)
            
            print(f"   📋 找到可用 Gemini 模型: {all_models}")

            def find_best_match(keywords, exclude_terms=[]):
                candidates = []
                for m in all_models:
                    # 排除
                    if any(ex in m for ex in exclude_terms): continue
                    # 匹配
                    for k in keywords:
                        if k in m:
                            candidates.append(m)
                            break
                if candidates:
                    # 排序：優先選版號新的 (假設命名規則中數字大或 exp/latest 在後)
                    # 這裡簡單用字母排序，通常 1.5 < 2.0
                    candidates.sort()
                    return candidates[-1]
                return None

            # 1. LITE: 找 flash-lite 或 flash-8b
            best_lite = find_best_match(['flash-lite', 'flash-8b'])
            
            # 2. FLASH: 找 flash, 但排除 lite/8b
            best_flash = find_best_match(['flash'], exclude_terms=['lite', '8b'])
            
            # 3. PRO: 找 pro, ultra, 或 3-flash (如果未來有的話) -> 這裡使用者指定要強一點的
            best_pro = find_best_match(['pro', 'ultra', '3-flash'])
            
            # 組裝
            final_map = {
                "LITE": best_lite if best_lite else fallback_map["LITE"],
                "FLASH": best_flash if best_flash else fallback_map["FLASH"],
                "PRO": best_pro if best_pro else fallback_map["PRO"]
            }
            
            return final_map
            
        except Exception as e:
            print(f"⚠️ 無法自動獲取模型列表 ({e})，使用預設配置。")
            return fallback_map

    def _init_api(self):
        """從 secrets.json 讀取 Gemini Key"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        secrets_path = os.path.join(base_dir, 'config', 'secrets.json')
        
        with open(secrets_path, 'r') as f:
            secrets = json.load(f)
            api_key = secrets.get('geminiApiKey')
            
        if not api_key:
            raise ValueError("❌ 錯誤：找不到 Gemini API Key！請檢查 secrets.json")
            
        genai.configure(api_key=api_key)

    def prepare_data_summary(self, df):
        """
        將數據轉化為 AI 可讀的摘要 (Prompt Engineering)
        [包含防呆機制]
        """
        # 1. 計算技術指標 (使用 try-except 保護)
        try:
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema200'] = ta.ema(df['close'], length=200)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        except Exception as e:
            print(f"⚠️ 指標計算部分失敗: {e}")

        # 取得最後一根 K 線
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- 防呆處理 ---
        # 如果 EMA200 是 NaN (數據不足)，就用收盤價代替，避免 NoneType 錯誤
        ema_val = last['ema200'] if pd.notna(last.get('ema200')) else last['close']
        trend_str = 'BULLISH' if last['close'] > ema_val else 'BEARISH'
        
        rsi_val = last['rsi'] if pd.notna(last.get('rsi')) else 50
        atr_val = last['atr'] if pd.notna(last.get('atr')) else 0
        # ----------------

        # 2. 建構語意化描述
        summary = f"""
        Market Data Summary for {last['timestamp']}:
        - Current Price: {last['close']:.4f}
        - Trend (EMA200): {trend_str} (EMA Level: {ema_val:.4f})
        - Momentum (RSI): {rsi_val:.1f}
        - Volatility (ATR): {atr_val:.4f}
        
        Recent Price Action:
        - Previous High: {prev['high']:.4f}
        - Previous Low: {prev['low']:.4f}
        - Previous Close: {prev['close']:.4f}
        """
        return summary

    async def analyze_market(self, df, custom_instruction=None, model_tier='FLASH'):    
        """    
        呼叫 Gemini 進行分析 (Async)
        :param model_tier: 'LITE' | 'FLASH' | 'PRO'    
        """
        selected_model = self.models.get(model_tier, self.models['FLASH'])
        model_name = self.model_map.get(model_tier, "Unknown")
        
        print(f"🧠 大腦正在思考中 [{model_tier}:{model_name}]...")
        
        data_summary = self.prepare_data_summary(df)
        
        # 系統提示詞 (System Prompt) - 賦予 AI 角色 [cite: 356-357]
        sys_prompt = """
        You are a strict crypto trading expert specialized in Price Action and SMC (Smart Money Concepts).
        Analyze the provided market summary.
        
        Your Goal: Identify high-probability setups (SFP, Order Blocks, or Trend Following).
        Risk Management: You are risk-averse. If market is choppy or unclear, output "signal": "NEUTRAL".
        
        Output Format: JSON only.
        Schema:
        {
            "signal": "LONG" | "SHORT" | "NEUTRAL",
            "confidence": 0.0 to 1.0,
            "entry_price": number,
            "stop_loss": number,
            "take_profit": number,
            "reasoning": "Use Traditional Chinese (繁體中文) to explain the reason in under 50 words."
        }
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 發送請求
                # 組合 Prompt (System + Custom + Data)
                full_prompt = sys_prompt
                if custom_instruction:
                    full_prompt += f"\n\n[SPECIFIC STRATEGY INSTRUCTIONS]\n{custom_instruction}"
                
                full_prompt += f"\n\n[MARKET DATA]\n{data_summary}"

                response = await selected_model.generate_content_async(full_prompt)
                
                # 解析 JSON
                decision = json.loads(response.text)
                return decision
                
            except Exception as e:
                is_quota_error = "429" in str(e) or "quota" in str(e).lower()
                if is_quota_error and attempt < max_retries - 1:
                    wait_time = 10 * (2 ** attempt) # 指數退避: 10s, 20s, 40s
                    print(f"⚠️ 觸發 API 頻率限制，等待 {wait_time} 秒後重試... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ 大腦當機 (API Error): {e}")
                    # 回傳一個安全的中立信號，避免報錯導致程式崩潰
                    return {"signal": "NEUTRAL", "reasoning": f"API Error: {str(e)[:50]}", "confidence": 0}