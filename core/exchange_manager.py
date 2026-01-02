"""
智能交易所管理器

自动检测并切换到可用的交易所，记住首选项
"""

import ccxt
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / 'data' / 'exchange_preference.json'

# 支持的交易所列表（按优先级排序）
SUPPORTED_EXCHANGES = ['binance', 'okx', 'bybit']


class ExchangeManager:
    """智能交易所管理器"""
    
    def __init__(self):
        self.preferred_exchange = None
        self.last_check_time = None
        self.load_preference()
    
    def load_preference(self):
        """加载保存的交易所偏好"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.preferred_exchange = data.get('preferred_exchange')
                    self.last_check_time = data.get('last_check_time')
                    logger.info(f"已加载首选交易所：{self.preferred_exchange}")
            except Exception as e:
                logger.warning(f"加载交易所偏好失败：{e}")
    
    def save_preference(self, exchange_name: str):
        """保存交易所偏好"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'preferred_exchange': exchange_name,
            'last_check_time': datetime.now().isoformat(),
            'reason': 'auto_detected'
        }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.preferred_exchange = exchange_name
        self.last_check_time = datetime.now().isoformat()
        logger.info(f"✅ 已保存首选交易所：{exchange_name}")
    
    def get_exchange(self, force_recheck: bool = False):
        """
        获取可用的交易所实例
        
        Args:
            force_recheck: 强制重新检查 Binance 是否可用
            
        Returns:
            ccxt.Exchange: 可用的交易所实例
        """
        # 如果有首选交易所且不强制检查，直接使用
        if self.preferred_exchange and not force_recheck:
            return self._create_exchange(self.preferred_exchange)
        
        # 否则依次尝试
        for exchange_name in SUPPORTED_EXCHANGES:
            exchange = self._create_exchange(exchange_name)
            if self._test_exchange(exchange):
                # 测试成功，保存为首选
                if exchange_name != self.preferred_exchange:
                    logger.info(f"🔄 切换到可用交易所：{exchange_name}")
                    self.save_preference(exchange_name)
                return exchange
        
        # 都失败了，返回默认并警告
        logger.error("❌ 所有交易所都不可用，使用默认 OKX")
        return ccxt.okx()
    
    def _create_exchange(self, exchange_name: str):
        """创建交易所实例"""
        exchange_class = getattr(ccxt, exchange_name)
        return exchange_class({
            'enableRateLimit': True,
            'timeout': 10000
        })
    
    def _test_exchange(self, exchange) -> bool:
        """测试交易所是否可用"""
        try:
            # 简单测试：获取 BTC 价格
            exchange.fetch_ticker('BTC/USDT')
            logger.info(f"✅ {exchange.id} 可用")
            return True
        except ccxt.BadRequest as e:
            if '451' in str(e) or 'restricted location' in str(e).lower():
                logger.warning(f"⚠️ {exchange.id} 地区限制")
                return False
        except Exception as e:
            logger.warning(f"⚠️ {exchange.id} 测试失败：{e}")
            return False
    
    def reset_preference(self):
        """重置偏好，下次会重新检测"""
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        self.preferred_exchange = None
        logger.info("🔄 已重置交易所偏好，下次启动会重新检测")


# 全局实例
_exchange_manager = ExchangeManager()


def get_exchange(force_recheck: bool = False):
    """
    获取可用的交易所（全局函数）
    
    Args:
        force_recheck: 强制重新检查 Binance 是否可用
        
    Returns:
        ccxt.Exchange: 可用的交易所实例
    """
    return _exchange_manager.get_exchange(force_recheck)


def reset_exchange_preference():
    """重置交易所偏好"""
    _exchange_manager.reset_preference()


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    print("测试交易所管理器...")
    exchange = get_exchange()
    print(f"当前使用：{exchange.id}")
    
    # 测试强制重检
    print("\n强制重新检查...")
    exchange = get_exchange(force_recheck=True)
    print(f"检查后使用：{exchange.id}")
