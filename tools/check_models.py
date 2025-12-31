# check_models.py
import google.generativeai as genai
import json
import os

def check():
    print("🔍 正在查詢可用模型清單...")
    
    # 1. 讀取 API Key
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        secrets_path = os.path.join(base_dir, 'config', 'secrets.json')
        with open(secrets_path, 'r') as f:
            secrets = json.load(f)
            api_key = secrets.get('geminiApiKey')
            
        if not api_key:
            print("❌ 錯誤：secrets.json 裡面沒有 geminiApiKey")
            return
            
        genai.configure(api_key=api_key)
        
        # 2. 列出模型
        found = False
        print("\n📋 Google 回傳的可用模型:")
        print("-" * 30)
        for m in genai.list_models():
            # 我們只關心能「產生內容 (generateContent)」的模型
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ {m.name}")
                found = True
        print("-" * 30)
        
        if not found:
            print("⚠️ 警告：沒有找到任何支援 generateContent 的模型。可能 API Key 權限有問題。")
            
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")

if __name__ == "__main__":
    check()