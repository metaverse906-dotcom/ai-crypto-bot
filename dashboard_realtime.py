#!/usr/bin/env python3
# dashboard_realtime.py - 即時看盤系統 v1.0
"""
即時看盤介面
- 多標的監控
- 互動式 K 線圖
- 市場指標整合
- 策略信號追蹤
"""

import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ccxt
from datetime import datetime, timedelta
import time
import requests

# ==================== 配置 ====================
st.set_page_config(
    page_title="即時看盤系統",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 資產列表
CORE_TIER1 = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
CORE_TIER2 = ['SOL/USDT', 'XRP/USDT', 'ADA/USDT']
SATELLITE = ['ARB/USDT', 'OP/USDT']
ALL_ASSETS = CORE_TIER1 + CORE_TIER2 + SATELLITE

# ==================== 數據提供者 ====================
class RealtimeDataProvider:
    """即時數據提供者"""
    
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
    
    @st.cache_data(ttl=10)
    def get_ticker(_self, symbol: str) -> dict:
        """獲取即時價格數據"""
        try:
            ticker = _self.exchange.fetch_ticker(symbol)
            return {
                'price': ticker['last'],
                'change_24h': ticker['percentage'],
                'volume_24h': ticker['quoteVolume'],
                'high_24h': ticker['high'],
                'low_24h': ticker['low']
            }
        except Exception as e:
            st.error(f"獲取 {symbol} 價格失敗: {e}")
            return None
    
    @st.cache_data(ttl=60)
    def get_ohlcv(_self, symbol: str, timeframe: str = '15m', limit: int = 200) -> pd.DataFrame:
        """獲取 K 線數據"""
        try:
            ohlcv = _self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            st.error(f"獲取 {symbol} K線失敗: {e}")
            return None
    
    def get_funding_rate(self, symbol: str) -> float:
        """獲取資金費率（期貨）"""
        try:
            # 需要切換到期貨市場
            futures_exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            funding = futures_exchange.fetch_funding_rate(symbol)
            return funding['fundingRate'] * 100 if funding else 0.0
        except Exception as e:
            st.sidebar.error(f"取得資金費率失敗: {e}")
            return 0.0
    
    @st.cache_data(ttl=300)
    def get_fear_greed_index(_self) -> dict:
        """獲取恐懼貪婪指數"""
        try:
            response = requests.get("https://api.alternative.me/fng/", timeout=5)
            data = response.json()
            return {
                'value': int(data['data'][0]['value']),
                'classification': data['data'][0]['value_classification']
            }
        except Exception as e:
            return {'value': 50, 'classification': 'Neutral'}
    
    @st.cache_data(ttl=300)
    def get_btc_dominance(_self) -> float:
        """獲取 BTC 市佔率"""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/global", timeout=5)
            data = response.json()
            return data['data']['market_cap_percentage']['btc']
        except Exception as e:
            st.error(f"計算指標失敗: {e}")
            return 0.0

# ==================== 信號檢測器 ====================
class SignalDetector:
    """策略信號檢測器"""
    
    def check_silver_bullet(self, df: pd.DataFrame) -> dict:
        """檢測 Silver Bullet 信號"""
        if df is None or len(df) < 210:
            return {'signal': None, 'reason': '數據不足'}
        
        # 計算 EMA 200
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        current = df.iloc[-1]
        prev_4h = df.iloc[-5:-1]  # 前 4 根 15m K線 = 1小時
        
        # 時段檢查（UTC）
        hour = current['timestamp'].hour
        if not ((2 <= hour < 5) or (10 <= hour < 11)):
            return {'signal': None, 'reason': '非交易時段'}
        
        # 掃蕩形態檢測
        lh_low = prev_4h['low'].min()
        lh_high = prev_4h['high'].max()
        
        # LONG 信號
        if current['low'] < lh_low and current['close'] > lh_low:
            if current['close'] > current['ema_200']:
                return {
                    'signal': 'LONG',
                    'reason': '掃蕩低點 + 收盤在 EMA 200 上方',
                    'entry': current['close'],
                    'sl': current['low'],
                    'tp': current['close'] + (current['close'] - current['low']) * 2.5
                }
        
        # SHORT 信號
        if current['high'] > lh_high and current['close'] < lh_high:
            if current['close'] < current['ema_200']:
                return {
                    'signal': 'SHORT',
                    'reason': '掃蕩高點 + 收盤在 EMA 200 下方',
                    'entry': current['close'],
                    'sl': current['high'],
                    'tp': current['close'] - (current['high'] - current['close']) * 2.5
                }
        
        return {'signal': None, 'reason': '無信號'}
    
    def check_hybrid_sfp(self, df: pd.DataFrame) -> dict:
        """檢測 Hybrid SFP 信號（4h）"""
        if df is None or len(df) < 250:
            return {'signal': None, 'reason': '數據不足'}
        
        # 計算指標
        df['ema_200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
        
        bb = ta.bbands(df['close'], length=20, std=2.0)
        if bb is not None:
            cols = bb.columns
            df['bb_upper'] = bb[cols[cols.str.startswith('BBU')][0]]
            df['bb_lower'] = bb[cols[cols.str.startswith('BBL')][0]]
            df['bw'] = bb[cols[cols.str.startswith('BBB')][0]]
        
        df['swing_high'] = df['high'].rolling(window=50).max().shift(1)
        df['swing_low'] = df['low'].rolling(window=50).min().shift(1)
        
        prev = df.iloc[-2]  # 使用前一根已完成的K線
        
        # SFP 偵測
        if prev['adx'] > 30:
            if prev['high'] > prev['swing_high'] and prev['close'] < prev['swing_high']:
                if prev['rsi'] > 60:
                    return {
                        'signal': 'SHORT',
                        'reason': 'SFP: 掃蕩高點 + RSI 超買',
                        'entry': prev['close'],
                        'sl': prev['high'],
                        'tp': prev['close'] - (prev['high'] - prev['close']) * 2.5
                    }
            
            if prev['low'] < prev['swing_low'] and prev['close'] > prev['swing_low']:
                if prev['rsi'] < 40:
                    return {
                        'signal': 'LONG',
                        'reason': 'SFP: 掃蕩低點 + RSI 超賣',
                        'entry': prev['close'],
                        'sl': prev['low'],
                        'tp': prev['close'] + (prev['close'] - prev['low']) * 2.5
                    }
        
        # Trend Breakout
        if prev['adx'] > 25 and pd.notna(prev.get('bb_upper')):
            if prev['close'] > prev['bb_upper'] and prev['close'] > prev['ema_200'] and prev['bw'] > 5.0:
                return {
                    'signal': 'LONG',
                    'reason': 'Trend: 突破布林上軌 + 趨勢確認',
                    'entry': prev['close'],
                    'sl': prev['close'] - 2 * prev['atr'],
                    'tp': prev['close'] + (2 * prev['atr']) * 2.5
                }
        
        return {'signal': None, 'reason': '無信號'}

# ==================== 初始化 ====================
@st.cache_resource
def get_data_provider():
    return RealtimeDataProvider()

@st.cache_resource
def get_signal_detector():
    return SignalDetector()

data_provider = get_data_provider()
detector = get_signal_detector()

# ==================== 樣式 ====================
st.markdown("""
<style>
    .big-font {font-size: 24px !important; font-weight: bold;}
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .signal-long {color: #00ff00; font-weight: bold;}
    .signal-short {color: #ff4444; font-weight: bold;}
    .no-signal {color: #888888;}
</style>
""", unsafe_allow_html=True)

# ==================== 側邊欄 ====================
with st.sidebar:
    st.header("⚙️ 設置")
    
    auto_refresh = st.checkbox("🔄 自動更新（10秒）", value=False)
    if auto_refresh:
        time.sleep(10)
        st.rerun()
    
    st.divider()
    
    st.subheader("📊 監控標的")
    show_tier1 = st.checkbox("核心 Tier1 (SB)", value=True)
    show_tier2 = st.checkbox("核心 Tier2 (SFP)", value=True)
    show_satellite = st.checkbox("衛星資產 (SFP)", value=True)
    
    selected_assets = []
    if show_tier1:
        selected_assets.extend(CORE_TIER1)
    if show_tier2:
        selected_assets.extend(CORE_TIER2)
    if show_satellite:
        selected_assets.extend(SATELLITE)
    
    st.divider()
    
    st.subheader("📈 K線設定")
    chart_timeframe = st.selectbox("時間框架", ['15m', '1h', '4h'], index=0)
    chart_limit = st.slider("K線數量", 50, 500, 200)
    
    st.divider()
    st.caption(f"更新時間: {datetime.now().strftime('%H:%M:%S')}")

# ==================== 主標題 ====================
st.markdown('<p class="big-font">📊 即時看盤系統 v1.0</p>', unsafe_allow_html=True)
st.markdown("**多標的監控 | 策略信號追蹤 | 市場指標整合**")

# ==================== 市場指標儀表板 ====================
st.subheader("🌍 市場指標")

col1, col2, col3, col4 = st.columns(4)

with col1:
    btc_dom = data_provider.get_btc_dominance()
    st.metric("BTC 市佔率", f"{btc_dom:.1f}%")

with col2:
    fg_index = data_provider.get_fear_greed_index()
    st.metric("恐懼貪婪指數", fg_index['value'], delta=fg_index['classification'])

with col3:
    funding = data_provider.get_funding_rate('BTC/USDT')
    st.metric("BTC 資金費率", f"{funding:.4f}%")

with col4:
    btc_ticker = data_provider.get_ticker('BTC/USDT')
    if btc_ticker:
        st.metric("BTC 24h 量", f"${btc_ticker['volume_24h']/1e9:.1f}B")

st.divider()

# ==================== 多標的監控網格 ====================
st.subheader("💹 多標的監控")

if not selected_assets:
    st.warning("請在側邊欄選擇要監控的標的")
else:
    # 3列網格顯示
    for i in range(0, len(selected_assets), 3):
        cols = st.columns(3)
        
        for j, col in enumerate(cols):
            if i + j < len(selected_assets):
                symbol = selected_assets[i + j]
                
                with col:
                    with st.container():
                        st.markdown(f"### {symbol.replace('/USDT', '')}")
                        
                        # 獲取價格數據
                        ticker = data_provider.get_ticker(symbol)
                        
                        if ticker:
                            # 價格與變化
                            price_color = "🟢" if ticker['change_24h'] > 0 else "🔴"
                            st.metric(
                                "價格",
                                f"${ticker['price']:.2f}" if ticker['price'] < 100 else f"${ticker['price']:.0f}",
                                delta=f"{ticker['change_24h']:+.2f}%"
                            )
                            
                            # 檢測信號
                            strategy = 'Silver Bullet' if symbol in CORE_TIER1 else 'Hybrid SFP'
                            tf = '15m' if symbol in CORE_TIER1 else '4h'
                            
                            df = data_provider.get_ohlcv(symbol, tf, limit=250)
                            
                            if df is not None:
                                if symbol in CORE_TIER1:
                                    signal_result = detector.check_silver_bullet(df)
                                else:
                                    signal_result = detector.check_hybrid_sfp(df)
                                
                                if signal_result['signal']:
                                    signal_class = 'signal-long' if signal_result['signal'] == 'LONG' else 'signal-short'
                                    st.markdown(f'<p class="{signal_class}">🎯 {signal_result["signal"]} 信號</p>', unsafe_allow_html=True)
                                    st.caption(signal_result['reason'])
                                else:
                                    st.markdown('<p class="no-signal">💤 無信號</p>', unsafe_allow_html=True)
                                    st.caption(signal_result.get('reason', ''))
                            
                            st.caption(f"策略: {strategy} ({tf})")
                        
                        st.divider()

st.divider()

# ==================== K線圖詳細視圖 ====================
st.subheader("📈 K線圖詳細視圖")

selected_symbol = st.selectbox("選擇標的", selected_assets)

if selected_symbol:
    df = data_provider.get_ohlcv(selected_symbol, chart_timeframe, limit=chart_limit)
    
    if df is not None:
        # 計算技術指標
        df['ema_200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # 創建子圖
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{selected_symbol} - {chart_timeframe}', 'RSI')
        )
        
        # K線
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price'
        ), row=1, col=1)
        
        # EMA 200
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['ema_200'],
            mode='lines',
            name='EMA 200',
            line=dict(color='orange', width=2)
        ), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['rsi'],
            mode='lines',
            name='RSI',
            line=dict(color='purple', width=1.5)
        ), row=2, col=1)
        
        # RSI 參考線
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(
            height=700,
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 顯示當前信號
        st.subheader("🎯 當前信號分析")
        
        if selected_symbol in CORE_TIER1:
            signal = detector.check_silver_bullet(df)
        else:
            signal = detector.check_hybrid_sfp(df)
        
        if signal['signal']:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("信號", signal['signal'])
            with col2:
                st.metric("入場", f"${signal['entry']:.2f}")
            with col3:
                st.metric("止損", f"${signal['sl']:.2f}")
            with col4:
                st.metric("止盈", f"${signal['tp']:.2f}")
            
            st.info(f"💡 {signal['reason']}")
        else:
            st.info(f"💤 {signal.get('reason', '無信號')}")

# ==================== 頁尾 ====================
st.divider()
st.caption("🤖 即時看盤系統 v1.0 | Powered by Binance API")
st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
