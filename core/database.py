# core/database.py
"""
交易系統資料庫存取層
使用 SQLite 替代 JSON，支持高效查詢與統計分析
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

class TradingDatabase:
    def __init__(self, db_path='data/trading.db'):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """獲取資料庫連接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典形式
        return conn
    
    def init_db(self):
        """初始化資料庫表結構"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 交易記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(20) NOT NULL,
                strategy VARCHAR(50) NOT NULL,
                side VARCHAR(10) NOT NULL,
                entry_price REAL NOT NULL,
                size REAL NOT NULL,
                leverage REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                status VARCHAR(20) DEFAULT 'OPEN',
                exit_price REAL,
                pnl REAL,
                pnl_pct REAL,
                close_timestamp DATETIME,
                close_reason VARCHAR(50),
                notes TEXT
            )
        ''')
        
        # 系統績效快照表（每日記錄）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                date DATE UNIQUE,
                total_equity REAL NOT NULL,
                daily_pnl REAL,
                total_trades INTEGER,
                win_rate REAL,
                sharpe_ratio REAL,
                max_drawdown REAL
            )
        ''')
        
        # 策略狀態表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_status (
                strategy_name VARCHAR(50) PRIMARY KEY,
                last_run DATETIME,
                trades_today INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                config TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 市場掃描記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(20) NOT NULL,
                strategy VARCHAR(50) NOT NULL,
                signal VARCHAR(10),
                indicators TEXT,
                executed BOOLEAN DEFAULT 0
            )
        ''')
        
        # 創建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON market_scans(timestamp)')
        
        conn.commit()
        conn.close()
        print("✅ 資料庫初始化完成")
    
    # ==================== 交易記錄操作 ====================
    
    def insert_trade(self, trade_data: Dict) -> int:
        """插入新交易記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (
                symbol, strategy, side, entry_price, size, leverage,
                stop_loss, take_profit, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data['symbol'],
            trade_data['strategy'],
            trade_data['side'],
            trade_data['entry_price'],
            trade_data['size'],
            trade_data['leverage'],
            trade_data.get('stop_loss'),
            trade_data.get('take_profit'),
            trade_data.get('status', 'OPEN'),
            trade_data.get('notes', '')
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def update_trade(self, trade_id: int, updates: Dict):
        """更新交易記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 動態構建 UPDATE 語句
        set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [trade_id]
        
        cursor.execute(f'''
            UPDATE trades SET {set_clause} WHERE id = ?
        ''', values)
        
        conn.commit()
        conn.close()
    
    def close_trade(self, trade_id: int, exit_price: float, close_reason: str):
        """關閉交易"""
        # 先獲取交易資訊計算 PnL
        trade = self.get_trade_by_id(trade_id)
        if not trade:
            return
        
        # 計算 PnL
        if trade['side'] == 'LONG':
            pnl_pct = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
        else:  # SHORT
            pnl_pct = ((trade['entry_price'] - exit_price) / trade['entry_price']) * 100
        
        pnl = pnl_pct * trade['size'] * trade['leverage'] / 100
        
        self.update_trade(trade_id, {
            'status': 'CLOSED',
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'close_timestamp': datetime.now().isoformat(),
            'close_reason': close_reason
        })
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:
        """根據 ID 獲取交易"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_open_trades(self) -> List[Dict]:
        """獲取所有開倉交易"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades WHERE status = "OPEN" ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_trades_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """獲取指定日期範圍的交易"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trades 
            WHERE DATE(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp DESC
        ''', (start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """獲取最近的交易記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 績效統計 ====================
    
    def save_performance_snapshot(self, snapshot: Dict):
        """保存績效快照"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO performance_snapshots (
                date, total_equity, daily_pnl, total_traces, win_rate,
                sharpe_ratio, max_drawdown
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot['date'],
            snapshot['total_equity'],
            snapshot.get('daily_pnl', 0),
            snapshot.get('total_trades', 0),
            snapshot.get('win_rate', 0),
            snapshot.get('sharpe_ratio', 0),
            snapshot.get('max_drawdown', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def get_performance_stats(self, days: int = 30) -> Dict:
        """獲取績效統計"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 獲取指定天數的交易
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'CLOSED' AND pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'CLOSED' THEN pnl ELSE 0 END) as total_pnl,
                AVG(CASE WHEN status = 'CLOSED' AND pnl > 0 THEN pnl END) as avg_win,
                AVG(CASE WHEN status = 'CLOSED' AND pnl < 0 THEN pnl END) as avg_loss
            FROM trades
            WHERE DATE(timestamp) >= ?
        ''', (start_date,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total_trades = row['total_trades'] or 0
            wins = row['wins'] or 0
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'total_trades': total_trades,
                'wins': wins,
                'losses': total_trades - wins,
                'win_rate': win_rate,
                'total_pnl': row['total_pnl'] or 0,
                'avg_win': row['avg_win'] or 0,
                'avg_loss': row['avg_loss'] or 0
            }
        
        return {}
    
    # ==================== 策略狀態 ====================
    
    def update_strategy_status(self, strategy_name: str, updates: Dict):
        """更新策略狀態"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 檢查是否存在
        cursor.execute('SELECT * FROM strategy_status WHERE strategy_name = ?', (strategy_name,))
        exists = cursor.fetchone()
        
        if exists:
            set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values()) + [datetime.now().isoformat(), strategy_name]
            cursor.execute(f'''
                UPDATE strategy_status 
                SET {set_clause}, updated_at = ?
                WHERE strategy_name = ?
            ''', values)
        else:
            cursor.execute('''
                INSERT INTO strategy_status (strategy_name, config)
                VALUES (?, ?)
            ''', (strategy_name, json.dumps(updates)))
        
        conn.commit()
        conn.close()
    
    def get_strategy_status(self, strategy_name: str) -> Optional[Dict]:
        """獲取策略狀態"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM strategy_status WHERE strategy_name = ?', (strategy_name,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # ==================== 市場掃描 ====================
    
    def log_market_scan(self, scan_data: Dict):
        """記錄市場掃描"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_scans (symbol, strategy, signal, indicators, executed)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            scan_data['symbol'],
            scan_data['strategy'],
            scan_data.get('signal', 'NONE'),
            json.dumps(scan_data.get('indicators', {})),
            scan_data.get('executed', False)
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_scans(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """獲取最近的市場掃描"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT * FROM market_scans 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (cutoff, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 簡化 API（兼容性包裝器）====================
    
    def log_trade(self, symbol: str, side: str, price: float, size: float, 
                  strategy: str, reason: str, pnl: float = 0) -> int:
        """簡化的交易記錄方法（兼容外部建議的 API）
        
        Args:
            symbol: 交易標的 (e.g., 'BTC/USDT')
            side: 方向 ('LONG' or 'SHORT')
            price: 價格
            size: 倉位大小
            strategy: 策略名稱
            reason: 交易原因/備註
            pnl: 盈虧（如果已知）
            
        Returns:
            trade_id: 交易記錄 ID
        """
        trade_data = {
            'symbol': symbol,
            'side': side,
            'entry_price': price,
            'size': size,
            'leverage': 1.0,  # 預設槓桿
            'strategy': strategy,
            'notes': reason
        }
        
        # 如果提供了 pnl，視為已關閉的交易
        if pnl != 0:
            trade_data['pnl'] = pnl
            trade_data['status'] = 'CLOSED'
            trade_data['close_timestamp'] = datetime.now().isoformat()
        
        return self.insert_trade(trade_data)
    
    def get_trades(self, limit: int = 100) -> pd.DataFrame:
        """簡化的查詢方法（返回 DataFrame）
        
        Args:
            limit: 返回記錄數量
            
        Returns:
            DataFrame 包含交易記錄
        """
        trades = self.get_recent_trades(limit)
        if trades:
            return pd.DataFrame(trades)
        return pd.DataFrame()
    
    # ==================== 資料匯出 ====================
    
    def export_trades_to_df(self, days: int = 30) -> pd.DataFrame:
        """匯出交易到 DataFrame"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        trades = self.get_trades_by_date_range(start_date, datetime.now().strftime('%Y-%m-%d'))
        
        if trades:
            df = pd.DataFrame(trades)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        
        return pd.DataFrame()
    
    def get_equity_curve(self, days: int = 30) -> pd.DataFrame:
        """獲取權益曲線數據"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        conn = self.get_connection()
        query = '''
            SELECT 
                DATE(close_timestamp) as date,
                SUM(pnl) as daily_pnl
            FROM trades
            WHERE status = 'CLOSED' AND DATE(close_timestamp) >= ?
            GROUP BY DATE(close_timestamp)
            ORDER BY date
        '''
        
        df = pd.read_sql_query(query, conn, params=(start_date,))
        conn.close()
        
        if not df.empty:
            df['cumulative_pnl'] = df['daily_pnl'].cumsum()
        
        return df

# 全局實例
db = TradingDatabase()
