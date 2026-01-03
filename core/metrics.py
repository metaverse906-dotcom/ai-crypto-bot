#!/usr/bin/env python3
# core/metrics.py
"""
Bot 性能和錯誤監控模組
追蹤 API 調用、錯誤率、快取命中率等指標
"""

import time
from typing import Dict, Optional
from datetime import datetime
import threading


class BotMetrics:
    """Bot 性能指標追蹤器（單例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.start_time = time.time()
        
        # API 統計
        self.api_calls = 0
        self.api_failures = 0
        self.api_response_times = []
        
        # 快取統計
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 指令統計
        self.command_counts = {}
        
        # 錯誤統計
        self.error_counts = {}
        
    def record_api_call(self, success: bool, response_time: float = 0.0, api_name: str = "unknown"):
        """記錄 API 調用"""
        self.api_calls += 1
        if not success:
            self.api_failures += 1
            self.error_counts[api_name] = self.error_counts.get(api_name, 0) + 1
        
        if response_time > 0:
            self.api_response_times.append(response_time)
            # 只保留最近 100 次
            if len(self.api_response_times) > 100:
                self.api_response_times.pop(0)
    
    def record_cache_hit(self, hit: bool):
        """記錄快取命中"""
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def record_command(self, command: str):
        """記錄指令使用"""
        self.command_counts[command] = self.command_counts.get(command, 0) + 1
    
    def get_uptime(self) -> str:
        """獲取運行時間"""
        uptime_seconds = int(time.time() - self.start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_avg_response_time(self) -> float:
        """獲取平均響應時間"""
        if not self.api_response_times:
            return 0.0
        return sum(self.api_response_times) / len(self.api_response_times)
    
    def get_health_report(self) -> str:
        """生成健康報告"""
        failure_rate = (self.api_failures / self.api_calls * 100) if self.api_calls > 0 else 0
        total_cache = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / total_cache * 100) if total_cache > 0 else 0
        avg_response = self.get_avg_response_time()
        
        # 最常用指令（前 5 名）
        top_commands = sorted(self.command_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        command_list = "\n".join([f"  • /{cmd}: {count} 次" for cmd, count in top_commands]) if top_commands else "  無數據"
        
        # 錯誤統計（前 3 名）
        top_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        error_list = "\n".join([f"  • {api}: {count} 次" for api, count in top_errors]) if top_errors else "  無錯誤 ✅"
        
        report = f"""
📊 **系統健康報告**

**運行狀態**
⏰ 運行時間: {self.get_uptime()}
📅 啟動時間: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}

**API 性能**
📡 總調用次數: {self.api_calls}
❌ 失敗次數: {self.api_failures}
📉 失敗率: {failure_rate:.1f}%
⚡ 平均響應: {avg_response:.2f}s

**快取效能**
🎯 命中次數: {self.cache_hits}
❌ 未命中: {self.cache_misses}
📈 命中率: {cache_hit_rate:.1f}%

**指令使用統計**
{command_list}

**錯誤統計**
{error_list}

**健康評分**: {"🟢 優秀" if failure_rate < 5 else "🟡 良好" if failure_rate < 15 else "🔴 需注意"}
"""
        return report.strip()
    
    def reset_stats(self):
        """重置統計數據"""
        self.api_calls = 0
        self.api_failures = 0
        self.api_response_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.command_counts = {}
        self.error_counts = {}


# 全域單例
metrics = BotMetrics()
