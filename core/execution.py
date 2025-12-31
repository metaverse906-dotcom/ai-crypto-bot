# core/execution.py
import ccxt.async_support as ccxt
import json
import os
import time
import pandas as pd
import uuid
import functools
from datetime import datetime
from core.persistence import StateManager
from core.risk_manager import RiskManager

def retry_async(retries=3, delay=1, backoff=2):
    """
    非同步重試裝飾器 (Exponential Backoff)
    針對網路錯誤進行自動重試
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _retries = retries
            _delay = delay
            while True:
                try:
                    return await func(*args, **kwargs)
                except (ccxt.NetworkError, ccxt.RequestTimeout) as e:
                    _retries -= 1
                    if _retries < 0:
                        print(f"❌ [Retry Failed] {func.__name__} 達到重試上限: {e}")
                        raise e # 重試耗盡，拋出異常
                    
                    print(f"⚠️ [Network Error] {func.__name__}: {e}. Retrying in {_delay}s...")
                    await asyncio.sleep(_delay)
                    _delay *= backoff
                except Exception as e:
                    # 其他非網路錯誤直接拋出 (例如參數錯誤)
                    raise e
        return wrapper
    return decorator

class ExecutionSystem:
    def __init__(self, symbol='SOL/USDT', timeframe='15m'):
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = None
        self.market_symbol = None
        self.exchange = None
        self.market_symbol = None
        self.state_manager = StateManager(file_path="data/paper_trades.json") # 專門存模擬交易
        self.paper_trades = self._load_paper_trades()
        self.max_daily_loss_pct = 0.20 # 20% 熔斷機制 (基於 2024 回測極端值 16%)
        self._init_exchange() # 初始化放在這裡
        self.risk_manager = RiskManager(self) # 初始化風險管理器
    
    def _load_paper_trades(self):
        """載入模擬交易紀錄 (含防呆)"""
        data = self.state_manager.load_state()
        
        # 確保必要的欄位都存在
        defaults = {
            "initial_balance": 1000.0,
            "active_positions": [], 
            "history": [], 
            "total_pnl": 0.0
        }
        
        if not data:
            return defaults
            
        # 補齊可能缺失的欄位 (例如檔案是被 Persistence 錯誤初始化的)
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
                
        return data
    
    def _init_exchange(self):
        """初始化交易所連線"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        secrets_path = os.path.join(base_dir, 'config', 'secrets.json')
        
        apiKey = ""
        secret = ""

        # 嘗試讀取檔案，如果讀不到或格式錯誤也沒關係，就當作沒鑰匙
        if os.path.exists(secrets_path):
            try:
                with open(secrets_path, 'r') as f:
                    secrets = json.load(f)
                    apiKey = secrets.get('apiKey', "")
                    secret = secrets.get('secret', "")
            except Exception as e:
                logging.warning(f"獲取倉位失敗: {e}")
                pass

        # 初始化 CCXT
        self.exchange = ccxt.binance({
            'apiKey': apiKey,
            'secret': secret,
            'options': {
                'defaultType': 'future', 
                'adjustForTimeDifference': True,
            },
            'enableRateLimit': True
        })

    async def get_balance(self):
        """
        獲取帳戶餘額 (Unified Wallet)
        真實模式: 返回 Binance USDT Free Balance
        模擬模式: 返回 Initial Balance + Total PnL
        """
        if self.exchange.apiKey and self.exchange.secret:
            try:
                balance = await self.exchange.fetch_balance()
                return float(balance['USDT']['free'])
            except Exception as e:
                print(f"❌ 無法獲取真實餘額: {e}")
                return 0.0
        else:
            # 模擬模式: 本金 + 損益
            return self.paper_trades.get('initial_balance', 1000.0) + self.paper_trades.get('total_pnl', 0.0)

    async def connect(self, verbose=False):
        """連線並進行基礎檢查 (Auto Retry Forever)"""
        while True:
            if verbose: print("🔗 正在連接 Binance Futures (公共接口)...")
            try:
                await self.exchange.load_markets()
                break # 成功則跳出迴圈
            except Exception as e:
                print(f"❌ 連線失敗: {e}")
                print("⏳ 5秒後嘗試重連...")
                await asyncio.sleep(5)
                continue  # 重試連線

        # 1. 統一符號處理 (Unified Symbols)
        try:
            market = self.exchange.market(self.symbol)
            self.market_symbol = market['symbol']
            if verbose: print(f"✅ 目標鎖定: {self.market_symbol}")
        except:
            self.market_symbol = self.symbol
            if verbose: print(f"⚠️ 符號警告: 使用原始符號 {self.market_symbol}")

        # 2. 判斷是否有鑰匙 (Private Mode Check)
        if self.exchange.apiKey and self.exchange.secret:
            if verbose: print("🔑 檢測到 API Key，嘗試獲取帳戶資訊...")
            try:
                position_mode = await self.exchange.fapiPrivate_get_positionsidedual()
                is_hedge_mode = position_mode['dualSidePosition']
                mode_str = "對沖模式 (Hedge)" if is_hedge_mode == 'true' else "單向模式 (One-way)"
                if verbose: print(f"ℹ️ 當前帳戶模式: {mode_str}")
                
                balance = await self.exchange.fetch_balance()
                usdt_free = balance['USDT']['free']
                if verbose: print(f"💰 帳戶餘額: {usdt_free:.2f} USDT")
            except Exception as e:
                if verbose: print(f"⚠️ 鑰匙似乎無效或權限不足: {e}")
        else:
            if verbose: print("👀 未檢測到 API Key，進入 [觀察模式] (只抓數據，不操作帳戶)")
        
        return True

    async def check_kill_switch(self):
        """檢查是否達到單日虧損上限 (目前僅實作模擬模式)"""
        # 1. 獲取今日開始時間戳
        now = datetime.now()
        start_of_day = datetime(now.year, now.month, now.day).timestamp()
        
        # 2. 計算今日已實現損益
        daily_pnl = 0.0
        for trade in self.paper_trades.get("history", []):
            if trade['exit_time'] >= start_of_day:
                daily_pnl += trade['pnl']
                
        # 3. 獲取當前餘額
        balance = await self.get_balance()
        if balance <= 0: return True # 破產保護
        
        # 4. 計算虧損百分比 (注意 daily_pnl 負數代表虧損)
        # 如果 daily_pnl 是 -50，balance 是 1000，則虧損 5%
        if daily_pnl < 0 and abs(daily_pnl) / balance >= self.max_daily_loss_pct:
            return True
            
        return False

    async def get_market_context(self):
        """
        獲取市場大環境數據 (Context Awareness)
        1. BTC 24h 漲跌幅 (Sentiments)
        2. Funding Rate (Crowdedness)
        """
        try:
            # 假設基台幣主要看 BTC
            ticker = await self.exchange.fetch_ticker('BTC/USDT')
            funding = await self.exchange.fetch_funding_rate('BTC/USDT')
            
            return {
                'btc_price': ticker['last'],
                'btc_change_24h': ticker['percentage'], # e.g. 2.5 (%)
                'funding_rate': funding['fundingRate'], # e.g. 0.0001
                'funding_rate_yearly': funding['fundingRate'] * 3 * 365 * 100 # 年化 %
            }
        except Exception as e:
            print(f"⚠️ 無法獲取市場 Context: {e}")
            return None

    @retry_async(retries=3, delay=2, backoff=2)
    async def fetch_ohlcv(self, limit=100):
        """獲取 K 線數據 (Auto Retry)"""
        try:
            # 如果還沒連線成功，symbol 可能還沒轉換，先用預設的
            symbol = self.market_symbol if self.market_symbol else self.symbol
            ohlcv = await self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"❌ 數據獲取失敗: {e}")
            return None

    async def fetch_ohlcv_for_symbol(self, symbol, timeframe, limit=100):
        """獲取指定幣種的 K 線數據 (供 RiskManager 使用)"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"⚠️ 數據獲取失敗 ({symbol}): {e}")
            return None

    @retry_async(retries=3, delay=1, backoff=2)
    async def fetch_ticker(self, symbol):
        """獲取最新價格 (Auto Retry)"""
        return await self.exchange.fetch_ticker(symbol)

    async def place_order(self, side, amount, stop_loss=None, take_profit=None, strategy='manual'):
        """下單執行 (支援真實與模擬，並記錄策略來源)"""
        
        # --- 0. 熔斷檢查 (Kill Switch) ---
        if await self.check_kill_switch():
            print(f"🛑 [KILL SWITCH] 觸發單日風控 (虧損 > {self.max_daily_loss_pct*100}%)，拒絕下單！")
            return
        
        market = self.market_symbol or self.symbol
        
        # --- 真實模式 (Real Mode) ---
        if self.exchange.apiKey and self.exchange.secret:
            print(f"🚀 [真實執行] {side} {amount} {market}")
            try:
                # 1. 市價開倉
                order = await self.exchange.create_order(
                    symbol=market,
                    type='market',
                    side=side,
                    amount=amount
                )
                print(f"   ✅ 開倉成功: ID {order.get('id')}")

                # 2. 掛出交易所端止損 (Hard SL)
                if stop_loss:
                    stop_side = 'sell' if side.lower() == 'buy' else 'buy'
                    try:
                        sl_order = await self.exchange.create_order(
                            symbol=market,
                            type='STOP_MARKET',
                            side=stop_side,
                            amount=amount,
                            params={
                                'stopPrice': stop_loss, # 觸發價格
                                'reduceOnly': True      # 關鍵：只減倉，不反開
                            }
                        )
                        print(f"   🛡️ [硬體止損] 已掛單: {stop_side} @ {stop_loss} (ID: {sl_order.get('id')})")
                    except Exception as sl_e:
                        print(f"   ❌ 止損掛單失敗 (危險!): {sl_e}")
                        # 這裡未來可以考慮加入撤銷開倉的邏輯 (Kill Switch)

            except Exception as e:
                print(f"❌ 下單交易失敗: {e}")
            return

        # --- 模擬模式 (Paper Mode) ---
        print(f"📝 [模擬交易] 開倉: {side} {market} 數量: {amount}")
        
        # 1. 取得當前價格作為入場價 (假設無滑價)
        try:
            ticker = await self.fetch_ticker(market)
            entry_price = ticker['last']
        except:
            print("❌ 無法獲取當前價格，模擬單取消")
            return

        # 2. 建立倉位物件
        position = {
            "id": str(uuid.uuid4())[:8],
            "strategy": strategy, # 記錄是誰下的單
            "symbol": market,
            "side": side.upper(),
            "entry_price": entry_price,
            "amount": amount,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_time": time.time(),
            "entry_time_str": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 3. 存入 JSON
        self.paper_trades["active_positions"].append(position)
        self.state_manager.save_state(self.paper_trades)
        print(f"   ✅ 模擬單已記錄 (ID: {position['id']}) @ {entry_price}")

    async def monitor_positions(self):
        """監控模擬倉位 (僅在無 API Key 時運作)"""
        # 如果是真實模式，這件事交給交易所的掛單，我們不插手
        if self.exchange.apiKey: 
            return

        if not self.paper_trades["active_positions"]:
            return

        print(f"\n🔎 [Paper Monitor] 正在監控 {len(self.paper_trades['active_positions'])} 個模擬倉位...")
        
        # 批量獲取最新價格 (簡單起見先用迴圈 fetch，量大可改 fetch_tickers)
        updated_positions = []
        history_updated = False
        
        for pos in self.paper_trades["active_positions"]:
            symbol = pos['symbol']
            try:
                ticker = await self.fetch_ticker(symbol)
                curr_price = ticker['last']
            except:
                updated_positions.append(pos)
                continue

            # 檢查出場條件
            exit_reason = None
            pnl = 0.0
            
            # LONG: SL (低於止損), TP (高於止盈)
            if pos['side'] == 'LONG':
                if pos['stop_loss'] and curr_price <= pos['stop_loss']:
                    exit_reason = "SL"
                elif pos['take_profit'] and curr_price >= pos['take_profit']:
                    exit_reason = "TP"
            
            # SHORT: SL (高於止損), TP (低於止盈)
            elif pos['side'] == 'SHORT':
                if pos['stop_loss'] and curr_price >= pos['stop_loss']:
                    exit_reason = "SL"
                elif pos['take_profit'] and curr_price <= pos['take_profit']:
                    exit_reason = "TP"

            if exit_reason:
                # 執行平倉結算
                if pos['side'] == 'LONG':
                    pnl = (curr_price - pos['entry_price']) * pos['amount']
                else:
                    pnl = (pos['entry_price'] - curr_price) * pos['amount']
                
                print(f"🚨 [Paper Trade] 觸發 {exit_reason}! {symbol} @ {curr_price}")
                print(f"   💰 PnL: {pnl:.4f} USDT")
                
                # 移入歷史
                completed_trade = pos.copy()
                completed_trade.update({
                    "exit_price": curr_price,
                    "exit_time": time.time(),
                    "exit_time_str": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "exit_reason": exit_reason,
                    "pnl": pnl
                })
                self.paper_trades["history"].append(completed_trade)
                self.paper_trades["total_pnl"] += pnl
                history_updated = True
            else:
                updated_positions.append(pos)
        
        # 如果有變動，存檔
        if history_updated:
            self.paper_trades["active_positions"] = updated_positions
            self.state_manager.save_state(self.paper_trades)
            print(f"📊 目前模擬總損益: {self.paper_trades['total_pnl']:.4f} USDT")

    async def close_session(self):
        """釋放交易所資源"""
        if self.exchange:
            await self.exchange.close()