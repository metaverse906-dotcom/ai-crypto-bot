# core/persistence.py
import json
import os
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, file_path="data/bot_state.json"):
        """
        初始化狀態管理器
        :param file_path: 狀態檔案儲存路徑 (預設在 data 目錄下，這樣 Docker Volume 可以保存)
        """
        # 確保路徑是絕對路徑，避免相對路徑問題
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.file_path = os.path.join(base_dir, file_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """如果檔案不存在，建立一個空的 JSON 結構"""
        if not os.path.exists(self.file_path):
            try:
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    initial_state = {
                        "silver_bullet": {
                            "last_trade_date": None,
                            "trades_today": 0
                        },
                        "hybrid_sfp": {
                            "last_signal_time": {} 
                        },
                        "system": {
                            "paper_balance": 1000.0,
                            "trade_history": []
                        }
                    }
                    json.dump(initial_state, f, indent=4)
                logger.info(f"🆕 已建立全新的狀態檔案: {self.file_path}")
            except Exception as e:
                logger.error(f"❌ 建立狀態檔案失敗: {e}")

    def load_state(self):
        """讀取狀態"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ 讀取狀態失敗: {e}")
            return {}

    def save_state(self, state):
        """保存狀態 (Atomic Write)"""
        temp_path = self.file_path + ".tmp"
        try:
            # 1. 先寫入暫存檔
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
                # 確保數據真正寫入硬碟 (防止斷電數據遺失)
                f.flush()
                os.fsync(f.fileno())
            
            # 2. 原子替換 (Atomic Replace)
            # 在 Linux/Windows 上，rename 是原子操作，要嘛成功要嘛失敗，不會有中間狀態
            os.replace(temp_path, self.file_path)
            # logger.info("💾 狀態已保存 (Atomic)")
            
        except Exception as e:
            logger.error(f"❌ 保存狀態失敗: {e}")
            # 如果失敗，嘗試刪除殘留的暫存檔
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass

    def update_strategy_state(self, strategy_name, key, value):
        """更新特定策略的狀態值"""
        state = self.load_state()
        
        if strategy_name not in state:
            state[strategy_name] = {}
            
        state[strategy_name][key] = value
        self.save_state(state)
        
    def get_strategy_state(self, strategy_name, key, default=None):
        """獲取特定策略的狀態值"""
        state = self.load_state()
        return state.get(strategy_name, {}).get(key, default)
