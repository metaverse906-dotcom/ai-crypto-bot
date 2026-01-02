"""
倉位管理系統（HIFO - Highest In First Out）

實現核心功能：
1. 追蹤每筆買入的成本批次（Lot Tracking）
2. HIFO 賣出邏輯：優先賣出高成本幣
3. 核心倉/交易倉自動分割
4. 平均成本動態計算
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """單筆買入記錄"""
    amount: float          # BTC 數量
    price: float           # 買入價格（USD）
    timestamp: datetime    # 買入時間
    category: str          # 'core' 或 'trade'
    note: str = ""         # 備註（如「MVRV 極度低估 3x 加碼」）
    
    @property
    def cost_basis(self) -> float:
        """成本基礎（總投入）"""
        return self.amount * self.price
    
    def to_dict(self) -> Dict:
        """轉換為字典（用於序列化）"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        """從字典還原"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class PositionManager:
    """
    HIFO 倉位管理器
    
    核心概念：
    - 每次買入自動分配：40% → 核心倉，60% → 交易倉
    - 核心倉：打死不賣，成為你的「低成本種子」
    - 交易倉：根據 MVRV 策略階梯式賣出
    - 賣出時使用 HIFO：優先賣出成本最高的幣
    """
    
    def __init__(self, core_ratio: float = 0.4, data_file: Optional[str] = None):
        """
        初始化倉位管理器
        
        Args:
            core_ratio: 核心倉比例（預設 40%）
            data_file: 持久化存儲文件路徑
        """
        self.core_ratio = core_ratio
        self.trade_ratio = 1.0 - core_ratio
        self.positions: List[Position] = []
        
        # 數據持久化
        if data_file:
            self.data_file = Path(data_file)
        else:
            self.data_file = Path("data/positions.json")
        
        self.load_positions()
    
    def add_buy(self, amount: float, price: float, note: str = "", force_category: str = None) -> Dict[str, Position]:
        """
        記錄買入並自動分割為核心倉/交易倉
        
        Args:
            amount: 買入總數量（BTC）
            price: 買入價格
            note: 備註（如「MVRV < 0.1 極度低估」）
            force_category: 強制指定類別（'core' 或 'trade'），用於初始化現有持倉
            
        Returns:
            dict: {'core': Position, 'trade': Position} 或 {'forced': Position}
        """
        timestamp = datetime.now()
        
        if force_category:
            # 手動指定類別（用於初始化現有持倉）
            forced_pos = Position(
                amount=amount,
                price=price,
                timestamp=timestamp,
                category=force_category,
                note=note
            )
            self.positions.append(forced_pos)
            
            logger.info(f"✅ 手動添加 {force_category} 倉: {amount:.6f} BTC @ ${price:,.0f}")
            self.save_positions()
            
            return {'forced': forced_pos}
        
        # 分割數量
        core_amount = amount * self.core_ratio
        trade_amount = amount * self.trade_ratio
        
        # 創建兩個 Position 記錄
        core_pos = Position(
            amount=core_amount,
            price=price,
            timestamp=timestamp,
            category='core',
            note=f"[核心倉] {note}"
        )
        
        trade_pos = Position(
            amount=trade_amount,
            price=price,
            timestamp=timestamp,
            category='trade',
            note=f"[交易倉] {note}"
        )
        
        self.positions.append(core_pos)
        self.positions.append(trade_pos)
        
        logger.info(
            f"✅ 買入記錄：{amount:.6f} BTC @ ${price:,.0f} "
            f"(核心: {core_amount:.6f}, 交易: {trade_amount:.6f})"
        )
        
        self.save_positions()
        
        return {'core': core_pos, 'trade': trade_pos}
    
    def execute_sell_hifo(self, amount: float, current_price: float) -> Dict[str, Any]:
        """
        執行 HIFO 賣出：優先賣出交易倉中成本最高的幣
        
        Args:
            amount: 要賣出的 BTC 數量
            current_price: 當前價格
            
        Returns:
            dict: {
                'sold_lots': List[Position],  # 被賣出的批次
                'total_revenue': float,        # 總收入
                'total_profit': float,         # 總獲利
                'avg_sell_cost': float        # 賣出幣的平均成本
            }
            
        Raises:
            ValueError: 交易倉數量不足
        """
        # 檢查交易倉可用數量
        trade_positions = [p for p in self.positions if p.category == 'trade']
        available = sum(p.amount for p in trade_positions)
        
        if amount > available:
            raise ValueError(
                f"交易倉數量不足！可用: {available:.6f} BTC, 需要: {amount:.6f} BTC"
            )
        
        # HIFO 排序：成本最高的排前面
        trade_positions.sort(key=lambda x: x.price, reverse=True)
        
        # 執行賣出
        sold_lots = []
        remaining_to_sell = amount
        total_revenue = 0
        total_cost_basis = 0
        
        for position in trade_positions:
            if remaining_to_sell <= 0:
                break
            
            # 計算這筆要賣多少
            sell_from_this_lot = min(position.amount, remaining_to_sell)
            
            # 計算獲利
            revenue = sell_from_this_lot * current_price
            cost = sell_from_this_lot * position.price
            profit = revenue - cost
            
            total_revenue += revenue
            total_cost_basis += cost
            remaining_to_sell -= sell_from_this_lot
            
            # 記錄已賣出的部分
            sold_lot = Position(
                amount=sell_from_this_lot,
                price=position.price,
                timestamp=position.timestamp,
                category='sold',
                note=f"於 {datetime.now().strftime('%Y-%m-%d')} 賣出 @ ${current_price:,.0f}"
            )
            sold_lots.append(sold_lot)
            
            logger.info(
                f"💰 賣出批次：{sell_from_this_lot:.6f} BTC "
                f"(成本 ${position.price:,.0f}) → 獲利 ${profit:,.2f}"
            )
            
            # 更新原 position（減少數量或移除）
            if sell_from_this_lot >= position.amount:
                self.positions.remove(position)
            else:
                position.amount -= sell_from_this_lot
        
        avg_sell_cost = total_cost_basis / amount
        total_profit = total_revenue - total_cost_basis
        
        logger.info(
            f"✅ HIFO 賣出完成：{amount:.6f} BTC @ ${current_price:,.0f}\n"
            f"   平均成本: ${avg_sell_cost:,.0f}\n"
            f"   總獲利: ${total_profit:,.2f}"
        )
        
        self.save_positions()
        
        return {
            'sold_lots': sold_lots,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'avg_sell_cost': avg_sell_cost
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        獲取持倉統計
        
        Returns:
            dict: {
                'total_btc': float,           # 總 BTC 數量
                'core_btc': float,            # 核心倉數量
                'trade_btc': float,           # 交易倉數量
                'avg_cost': float,            # 總平均成本
                'core_avg_cost': float,       # 核心倉平均成本
                'trade_avg_cost': float,      # 交易倉平均成本
                'total_invested': float,      # 總投入金額
                'num_positions': int         # 持倉批次數
            }
        """
        core_positions = [p for p in self.positions if p.category == 'core']
        trade_positions = [p for p in self.positions if p.category == 'trade']
        
        core_btc = sum(p.amount for p in core_positions)
        trade_btc = sum(p.amount for p in trade_positions)
        total_btc = core_btc + trade_btc
        
        total_invested = sum(p.cost_basis for p in self.positions)
        
        avg_cost = total_invested / total_btc if total_btc > 0 else 0
        
        core_invested = sum(p.cost_basis for p in core_positions)
        core_avg_cost = core_invested / core_btc if core_btc > 0 else 0
        
        trade_invested = sum(p.cost_basis for p in trade_positions)
        trade_avg_cost = trade_invested / trade_btc if trade_btc > 0 else 0
        
        return {
            'total_btc': total_btc,
            'core_btc': core_btc,
            'trade_btc': trade_btc,
            'avg_cost': avg_cost,
            'core_avg_cost': core_avg_cost,
            'trade_avg_cost': trade_avg_cost,
            'total_invested': total_invested,
            'num_positions': len(self.positions)
        }
    
    def get_unrealized_pnl(self, current_price: float) -> Dict[str, Any]:
        """
        計算未實現盈虧
        
        Args:
            current_price: 當前 BTC 價格
            
        Returns:
            dict: {
                'current_value': float,       # 當前市值
                'total_invested': float,      # 總投入
                'unrealized_pnl': float,      # 未實現盈虧
                'roi_pct': float             # 報酬率 %
            }
        """
        stats = self.get_stats()
        current_value = stats['total_btc'] * current_price
        total_invested = stats['total_invested']
        unrealized_pnl = current_value - total_invested
        roi_pct = (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'current_value': current_value,
            'total_invested': total_invested,
            'unrealized_pnl': unrealized_pnl,
            'roi_pct': roi_pct
        }
    
    def save_positions(self):
        """保存持倉到文件"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'core_ratio': self.core_ratio,
            'positions': [p.to_dict() for p in self.positions],
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_positions(self):
        """從文件加載持倉"""
        if not self.data_file.exists():
            logger.info("無持倉數據文件，從空開始")
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.positions = [Position.from_dict(p) for p in data['positions']]
            logger.info(f"✅ 加載 {len(self.positions)} 筆持倉記錄")
            
        except Exception as e:
            logger.error(f"加載持倉失敗: {e}")
    
    def print_summary(self, current_price: Optional[float] = None):
        """
        打印持倉摘要（用於調試）
        
        Args:
            current_price: 當前價格（可選）
        """
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 倉位摘要")
        print("=" * 60)
        print(f"總持倉：{stats['total_btc']:.6f} BTC")
        print(f"  ├─ 核心倉：{stats['core_btc']:.6f} BTC (平均成本 ${stats['core_avg_cost']:,.0f})")
        print(f"  └─ 交易倉：{stats['trade_btc']:.6f} BTC (平均成本 ${stats['trade_avg_cost']:,.0f})")
        print(f"\n總投入：${stats['total_invested']:,.2f}")
        print(f"平均成本：${stats['avg_cost']:,.2f}")
        print(f"持倉批次：{stats['num_positions']} 筆")
        
        if current_price:
            pnl = self.get_unrealized_pnl(current_price)
            print(f"\n當前價格：${current_price:,.0f}")
            print(f"當前市值：${pnl['current_value']:,.2f}")
            print(f"未實現盈虧：${pnl['unrealized_pnl']:,.2f} ({pnl['roi_pct']:+.2f}%)")
        
        print("=" * 60)


if __name__ == '__main__':
    # 測試用例
    logging.basicConfig(level=logging.INFO)
    
    print("\n🧪 倉位管理系統測試\n")
    
    # 創建管理器（40% 核心倉）
    pm = PositionManager(core_ratio=0.4, data_file="test_positions.json")
    
    # 模擬歷史買入
    print("📝 模擬買入歷史：")
    pm.add_buy(amount=0.5, price=20000, note="熊市底部")
    pm.add_buy(amount=0.3, price=35000, note="回升階段")
    pm.add_buy(amount=1.0, price=60000, note="牛市追高（高成本）")
    
    # 查看持倉
    pm.print_summary(current_price=72000)
    
    # 測試 HIFO 賣出
    print("\n💸 執行 HIFO 賣出測試（賣出 0.5 BTC）：")
    result = pm.execute_sell_hifo(amount=0.5, current_price=72000)
    
    print(f"\n賣出結果：")
    print(f"  總收入：${result['total_revenue']:,.2f}")
    print(f"  總獲利：${result['total_profit']:,.2f}")
    print(f"  平均成本：${result['avg_sell_cost']:,.2f}")
    
    # 賣出後的持倉
    pm.print_summary(current_price=72000)
