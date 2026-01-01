#!/usr/bin/env python3
# dashboard_unified.py - 統一交易儀表板 v1.0
"""
整合式交易系統儀表板
- 機器人狀態監控
- 策略詳情分析（K線圖 + 交易標記）
- 即時看盤
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime
import pandas_ta as ta
import vectorbt as vbt

# 頁面配置
st.set_page_config(
    page_title="交易系統統一儀表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 數據載入函數 ====================

@st.cache_data(ttl=5)
def load_paper_trades():
    """載入模擬交易紀錄"""
    try:
        with open('data/paper_trades.json', 'r') as f:
            return json.load(f)
    except:
        return {"initial_balance": 1000.0, "active_positions": [], "history": [], "total_pnl": 0.0}

@st.cache_data(ttl=60)
def load_backtest_data(strategy_name):
    """載入回測數據（從 CSV）"""
    try:
        # 根據策略名稱對應文件
        if strategy_name == "Silver Bullet":
            df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        else:  # Hybrid SFP
            df = pd.read_csv('data/backtest/BTC_USDT_15m_2023-2024.csv')
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"無法載入回測數據: {e}")
        return None

def get_strategy_trades(all_trades, strategy_name, data_source):
    """過濾特定策略的交易紀錄"""
    if data_source == "實盤交易":
        # 從 history 過濾
        history = all_trades.get('history', [])
        strategy_map = {
            "Silver Bullet": "SilverBullet",
            "Hybrid SFP": "HybridSFP"
        }
        filtered = [t for t in history if t.get('strategy') == strategy_map.get(strategy_name)]
        return pd.DataFrame(filtered) if filtered else pd.DataFrame()
    else:
        # 回測數據（模擬生成）
        return pd.DataFrame()

# ==================== K線圖繪製 ====================

def plot_chart_with_trades(df, trades, strategy_name):
    """繪製帶交易標記的K線圖"""
    
    # 計算技術指標
    df['ema_200'] = ta.ema(df['close'], length=200)
    
    if strategy_name == "Silver Bullet":
        # 15m 時間框架
        timeframe_label = "15分鐘"
    else:
        # 4h 時間框架，需要聚合
        df = df.set_index('timestamp')
        df = df.resample('4H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        df['ema_200'] = ta.ema(df['close'], length=200)
        timeframe_label = "4小時"
    
    # 創建圖表
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{strategy_name} K線圖 ({timeframe_label})', '成交量')
    )
    
    # K線
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='價格',
        showlegend=False
    ), row=1, col=1)
    
    # EMA 200
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['ema_200'],
        mode='lines',
        name='EMA 200',
        line=dict(color='orange', width=2)
    ), row=1, col=1)
    
    # 成交量
    colors = ['red' if df['close'].iloc[i] < df['open'].iloc[i] else 'green' 
              for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['volume'],
        name='成交量',
        marker_color=colors,
        showlegend=False
    ), row=2, col=1)
    
    # 訂單塊視覺化（支撐/阻力區域）
    last_high = df['high'].tail(100).max()
    last_low = df['low'].tail(100).min()
    
    # 阻力區域（Resistance Zone）
    fig.add_hrect(
        y0=last_high * 0.999,
        y1=last_high,
        line_width=0,
        fillcolor="red",
        opacity=0.2,
        annotation_text="Resistance",
        annotation_position="top right",
        row=1, col=1
    )
    
    # 支撐區域（Support Zone）  
    fig.add_hrect(
        y0=last_low,
        y1=last_low * 1.001,
        line_width=0,
        fillcolor="green",
        opacity=0.2,
        annotation_text="Support",
        annotation_position="bottom right",
        row=1, col=1
    )
    
    # 標記交易點
    if not trades.empty and 'entry_time' in trades.columns:
        # 進場點（綠色三角形）
        entry_times = pd.to_datetime(trades['entry_time'], unit='s')
        entry_prices = trades['entry_price']
        
        fig.add_trace(go.Scatter(
            x=entry_times,
            y=entry_prices,
            mode='markers',
            name='進場',
            marker=dict(
                symbol='triangle-up',
                size=15,
                color='lime',
                line=dict(color='darkgreen', width=2)
            )
        ), row=1, col=1)
        
        # 出場點（紅色X）- 如果有
        if 'exit_time' in trades.columns:
            closed_trades = trades[trades['exit_time'].notna()]
            if not closed_trades.empty:
                exit_times = pd.to_datetime(closed_trades['exit_time'], unit='s')
                exit_prices = closed_trades['exit_price']
                
                fig.add_trace(go.Scatter(
                    x=exit_times,
                    y=exit_prices,
                    mode='markers',
                    name='出場',
                    marker=dict(
                        symbol='x',
                        size=15,
                        color='red',
                        line=dict(width=2)
                    )
                ), row=1, col=1)
    
    fig.update_layout(
        height=700,
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        template='plotly_dark'
    )
    
    fig.update_xaxes(title_text="時間", row=2, col=1)
    fig.update_yaxes(title_text="價格 (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    return fig

# ==================== 頁面 1: 機器人狀態 ====================

def show_bot_status():
    st.header("🤖 機器人狀態")
    
    trades_data = load_paper_trades()
    
    # 關鍵指標
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        balance = trades_data.get('initial_balance', 1000) + trades_data.get('total_pnl', 0)
        st.metric("當前權益", f"${balance:.2f}", 
                  delta=f"{trades_data.get('total_pnl', 0):+.2f}")
    
    with col2:
        active_count = len(trades_data.get('active_positions', []))
        st.metric("當前倉位", active_count)
    
    with col3:
        history = trades_data.get('history', [])
        total_trades = len(history)
        st.metric("總交易次數", total_trades)
    
    with col4:
        if history:
            wins = len([t for t in history if t.get('pnl', 0) > 0])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            st.metric("勝率", f"{win_rate:.1f}%")
        else:
            st.metric("勝率", "0%")
    
    st.divider()
    
    # 當前開倉
    st.subheader("📋 當前開倉")
    active_positions = trades_data.get('active_positions', [])
    
    if active_positions:
        df_active = pd.DataFrame(active_positions)
        st.dataframe(df_active[['id', 'strategy', 'symbol', 'side', 'entry_price', 
                                 'stop_loss', 'take_profit', 'entry_time_str']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("目前無開倉")
    
    st.divider()
    
    # 權益曲線
    st.subheader("📈 權益曲線")
    
    if history:
        df_history = pd.DataFrame(history)
        df_history['timestamp'] = pd.to_datetime(df_history['exit_time'], unit='s')
        df_history = df_history.sort_values('timestamp')
        df_history['cumulative_pnl'] = df_history['pnl'].cumsum()
        df_history['equity'] = trades_data.get('initial_balance', 1000) + df_history['cumulative_pnl']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_history['timestamp'],
            y=df_history['equity'],
            mode='lines+markers',
            name='權益',
            line=dict(color='#00ff00', width=2),
            fill='tozeroy',
            fillcolor='rgba(0,255,0,0.1)'
        ))
        
        fig.update_layout(
            title="權益變化",
            xaxis_title="時間",
            yaxis_title="權益 (USDT)",
            height=400,
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無交易歷史")

# ==================== 頁面 2: 策略詳情 ====================

def show_strategy_details():
    st.header("📊 策略詳情")
    
    # 策略選擇
    col1, col2 = st.columns([1, 1])
    
    with col1:
        strategy = st.selectbox("選擇策略", ["Silver Bullet", "Hybrid SFP"])
    
    with col2:
        data_source = st.radio("數據來源", ["實盤交易", "回測紀錄"], horizontal=True)
    
    st.divider()
    
    # 載入數據
    all_trades = load_paper_trades()
    trades_df = get_strategy_trades(all_trades, strategy, data_source)
    
    # K線圖區域
    st.subheader(f"📈 {strategy} K線圖")
    
    # 載入K線數據
    backtest_df = load_backtest_data(strategy)
    
    if backtest_df is not None:
        # 只顯示最近的數據
        backtest_df = backtest_df.tail(500)
        
        # 繪製K線圖 + 交易標記
        fig = plot_chart_with_trades(backtest_df, trades_df, strategy)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("無法載入K線數據")
    
    st.divider()
    
    # 交易紀錄列表
    st.subheader(f"📜 {data_source}紀錄")
    
    if not trades_df.empty:
        # 格式化顯示
        display_df = trades_df[['symbol', 'side', 'entry_price', 'exit_price', 
                                 'pnl', 'exit_reason', 'entry_time_str']] if 'exit_price' in trades_df.columns else trades_df
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # 統計摘要
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("總交易", len(trades_df))
        with col2:
            if 'pnl' in trades_df.columns:
                total_pnl = trades_df['pnl'].sum()
                st.metric("總盈虧", f"${total_pnl:.2f}")
        with col3:
            if 'pnl' in trades_df.columns:
                wins = len(trades_df[trades_df['pnl'] > 0])
                win_rate = (wins / len(trades_df) * 100) if len(trades_df) > 0 else 0
                st.metric("勝率", f"{win_rate:.1f}%")
    else:
        st.info(f"暫無 {data_source} 紀錄")

# ==================== 頁面 3: 即時看盤 ====================

def show_realtime_monitor():
    st.header("💹 即時看盤")
    st.info("此功能保留給即時看盤介面，建議直接訪問原 dashboard_realtime.py")
    
    st.markdown("""
    **即時看盤功能**包含：
    - 8個標的即時價格監控
    - 互動式K線圖（15m/1h/4h）
    - 市場指標（BTC市佔率、恐懼貪婪指數、資金費率）
    - 策略信號即時檢測
    
    **訪問方式**：
    如果 Docker 容器運行中，訪問：http://localhost:8501
    """)

# ==================== 頁面 4: 回測實驗室 ====================

def show_backtest_lab():
    st.header("🧪 策略回測實驗室")
    st.caption("使用 VectorBT 快速驗證策略想法")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("#### 回測參數設定")
        test_strategy = st.selectbox("測試策略", ["雙均線交叉", "RSI 超買超賣"])
        
        if test_strategy == "雙均線交叉":
            fast_ma = st.number_input("快線週期", 5, 50, 10)
            slow_ma = st.number_input("慢線週期", 20, 200, 50)
        else:
            rsi_period = st.number_input("RSI 週期", 7, 21, 14)
            rsi_upper = st.slider("超買線", 60, 90, 70)
            rsi_lower = st.slider("超賣線", 10, 40, 30)
        
        st.divider()
        initial_cash = st.number_input("初始資金 (USDT)", 100, 10000, 1000)
        fees = st.slider("手續費 (%)", 0.0, 0.5, 0.1, 0.01) / 100
        run_backtest = st.button("🚀 執行回測", type="primary", use_container_width=True)
    
    with col2:
        if run_backtest:
            with st.spinner("執行回測中..."):
                df = load_backtest_data("Silver Bullet")
                if df is not None and len(df) > 200:
                    try:
                        if test_strategy == "雙均線交叉":
                            ma_fast = vbt.MA.run(df['close'], fast_ma)
                            ma_slow = vbt.MA.run(df['close'], slow_ma)
                            entries = ma_fast.ma_crossed_above(ma_slow)
                            exits = ma_fast.ma_crossed_below(ma_slow)
                        else:
                            rsi = vbt.RSI.run(df['close'], rsi_period)
                            entries = rsi.rsi_crossed_below(rsi_lower)
                            exits = rsi.rsi_crossed_above(rsi_upper)
                        
                        pf = vbt.Portfolio.from_signals(df['close'], entries, exits, init_cash=initial_cash, fees=fees)
                        st.success("✅ 回測完成！")
                        
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("總回報率", f"{pf.total_return()*100:.2f}%")
                        with c2:
                            st.metric("總交易", int(pf.stats()['Total Trades']))
                        with c3:
                            st.metric("勝率", f"{pf.stats()['Win Rate [%]']:.1f}%")
                        with c4:
                            st.metric("Sharpe", f"{pf.stats()['Sharpe Ratio']:.2f}")
                        
                        st.line_chart(pf.value(), height=400)
                        with st.expander("📊 詳細統計"):
                            st.write(pf.stats())
                    except Exception as e:
                        st.error(f"回測失敗: {e}")
                else:
                    st.warning("資料不足")
        else:
            st.info("👈 設定參數後點擊「執行回測」")

# ==================== 主程序 ====================

def main():
    # 側邊欄
    with st.sidebar:
        st.title("📊 交易系統")
        st.caption("統一儀表板 v1.0")
        
        st.divider()
        
        # 頁面選擇
        page = st.radio(
            "選擇頁面",
            ["🤖 機器人狀態", "📊 策略詳情", "💹 即時看盤", "🧪 回測實驗室"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # 系統信息
        st.caption(f"更新時間: {datetime.now().strftime('%H:%M:%S')}")
        
        if st.button("🔄 刷新數據"):
            st.cache_data.clear()
            st.rerun()
    
    # 主標題
    st.title("📊 加密貨幣交易系統")
    st.markdown("**統一儀表板** | 機器人監控 + 策略分析 + 即時看盤")
    
    st.divider()
    
    # 路由到對應頁面
    if page == "🤖 機器人狀態":
        show_bot_status()
    elif page == "📊 策略詳情":
        show_strategy_details()
    elif page == "💹 即時看盤":
        show_realtime_monitor()
    else:
        show_backtest_lab()
    
    # 頁尾
    st.divider()
    st.caption("🤖 技術交易系統 v5.0 | 數據驗證優化版")

if __name__ == "__main__":
    main()
