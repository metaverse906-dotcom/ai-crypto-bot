# dashboard.py - 專業級交易監控系統 v3.0 (準確配置版)
"""
技術交易系統監控介面
呈現準確的優化歷程與實盤數據
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import os
import time

# 導入資料庫
try:
    from core.database import TradingDatabase
    db = TradingDatabase()
except ImportError:
    db = None

# ==================== 頁面配置 ====================
st.set_page_config(
    page_title="技術交易監控系統",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 樣式 ====================
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: bold; color: #1f77b4;}
    .positive {color: #00ff00; font-weight: bold;}
    .negative {color: #ff4444; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ==================== 資料載入 ====================
@st.cache_data(ttl=5)
def load_trades():
    if db:
        return db.get_recent_trades(limit=1000)
    return []

@st.cache_data(ttl=5)
def get_performance_stats(days=30):
    if db:
        return db.get_performance_stats(days)
    return {}

def get_open_positions():
    if db:
        return db.get_open_trades()
    return []

# ==================== 側邊欄 ====================
with st.sidebar:
    st.header("⚙️ 控制面板")
    auto_refresh = st.checkbox("🔄 即時更新 (5秒)", value=True)
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    
    days_range = st.selectbox("📅 數據範圍", [7, 14, 30, 60, 90], index=2)
    st.divider()
    
    st.subheader("🔴 系統狀態")
    st.markdown('<p style="color:#00ff00">● 運行中</p>', unsafe_allow_html=True)
    st.caption("技術交易系統 v5.0")
    st.caption(f"更新: {datetime.now().strftime('%H:%M:%S')}")
    
    st.divider()
    st.subheader("📊 當前配置")
    st.markdown("**Silver Bullet (15m)**")
    st.caption("盈虧比 1:2.5 | EMA 200")
    st.caption("資產: BTC/ETH/BNB")
    
    st.markdown("**Hybrid SFP (4h)**")
    st.caption("盈虧比 1:2.5 | RSI 60/40")
    st.caption("ADX > 30 | EMA 200")

# ==================== 主標題 ====================
st.markdown('<p class="main-header">🤖 技術交易監控系統 v5.0</p>', unsafe_allow_html=True)
st.markdown("**數據驗證優化版** | 零 AI 成本 | 全功能監控")

# ==================== 頁面導航 ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 績效總覽",
    "🔧 優化歷程", 
    "📅 多時間框架",
    "🔥 風險熱力圖",
    "📜 交易記錄"
])

# ==================== Tab 1: 績效總覽 ====================
with tab1:
    stats = get_performance_stats(days_range)
    
    if stats and stats.get('total_trades', 0) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_pnl = stats.get('total_pnl', 0)
            st.metric("總損益", f"${total_pnl:.2f}", delta=f"{(total_pnl/1000*100):.2f}%")
        with col2:
            win_rate = stats.get('win_rate', 0)
            st.metric("勝率", f"{win_rate:.1f}%")
        with col3:
            st.metric("總交易", stats.get('total_trades', 0))
        with col4:
            avg_win = stats.get('avg_win', 0)
            avg_loss = stats.get('avg_loss', 0)
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            st.metric("盈虧因子", f"{profit_factor:.2f}")
    else:
        st.info("📭 暫無交易數據")
    
    st.divider()
    
    # 當前開倉
    st.subheader("🔴 當前開倉")
    open_positions = get_open_positions()
    
    if open_positions:
        for trade in open_positions:
            col1, col2, col3, col4 = st.columns([2,1,1,1])
            with col1:
                st.markdown(f"**{trade.get('symbol')}** | {trade.get('strategy')} | {trade.get('side')}")
            with col2:
                st.metric("入場", f"${trade.get('entry_price', 0):.2f}")
            with col3:
                st.metric("止損", f"${trade.get('stop_loss', 0):.2f}")
            with col4:
                st.metric("止盈", f"${trade.get('take_profit', 0):.2f}")
            st.divider()
    else:
        st.info("📭 目前無開倉")
    
    # 權益曲線
    st.subheader("📈 權益曲線")
    trades = load_trades()
    if trades:
        df = pd.DataFrame(trades)
        closed = df[df['status'] == 'CLOSED'].copy()
        
        if len(closed) > 0:
            closed['timestamp'] = pd.to_datetime(closed['timestamp'])
            closed = closed.sort_values('timestamp')
            closed['cumulative_pnl'] = closed['pnl'].cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=closed['timestamp'], y=closed['cumulative_pnl'],
                mode='lines+markers', name='累積損益',
                line=dict(color='#1f77b4', width=2),
                fill='tozeroy'
            ))
            fig.update_layout(title="累積損益曲線", height=400)
            st.plotly_chart(fig, use_container_width=True)

# ==================== Tab 2: 優化歷程 ====================
with tab2:
    st.header("🔧 系統優化歷程")
    
    st.info("💡 以下展示數據驗證驅動的參數優化過程（2023-2024 回測對比）")
    
    # Hybrid SFP 優化
    st.subheader("📊 Hybrid SFP 策略優化")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**階段 1：ADX 邏輯修正**")
        st.metric("修正前 (ADX < 30)", "-72.45%", delta="震盪市邏輯")
        st.metric("修正後 (ADX > 30)", "+12.15%", delta="+84.6% 改善")
        st.caption("✅ 發現邏輯錯誤並修正")
    
    with col2:
        st.markdown("**階段 2：策略混合**")
        st.metric("SFP 單獨", "+12.15%")
        st.metric("SFP + Trend", "+18.75%", delta="+6.6% 協同效應")
        st.caption("✅ 混合策略優於拆分")
    
    with col3:
        st.markdown("**階段 3：RSI 優化**")
        st.metric("RSI 55/45", "+18.75%")
        st.metric("RSI 60/40", "+24.07%", delta="+5.32% 提升")
        st.caption("✅ 最終優化配置")
    
    st.success("🎉 總改進：-72.45% → +24.07% (+96.52%)")
    
    st.divider()
    
    # 參數對比表
    st.subheader("📋 最終優化配置")
    
    config_data = {
        '策略': ['Hybrid SFP', 'Hybrid SFP', 'Silver Bullet', 'Silver Bullet'],
        '參數': ['ADX', 'RSI', '盈虧比', 'EMA'],
        '優化前': ['< 30', '55/45', '1:2', '50/100/200 測試'],
        '優化後': ['> 30 ✅', '60/40 ✅', '1:2.5 ✅', '200 ✅'],
        '改善': ['+84.6%', '+5.32%', '相對最優', '相對最優']
    }
    
    st.table(pd.DataFrame(config_data))
    
    st.warning("⚠️ 注意：以上數據來自簡化回測環境，用於參數對比。實盤績效需實際運行驗證。")

# ==================== Tab 3: 多時間框架 ====================
with tab3:
    st.header("📅 多時間框架分析")
    
    timeframe = st.selectbox("時間粒度", ["每日", "每週", "每月"])
    
    trades = load_trades()
    if trades:
        df = pd.DataFrame(trades)
        closed = df[df['status'] == 'CLOSED'].copy()
        
        if len(closed) > 0:
            closed['timestamp'] = pd.to_datetime(closed['timestamp'])
            
            if timeframe == "每日":
                closed['period'] = closed['timestamp'].dt.date
            elif timeframe == "每週":
                closed['period'] = closed['timestamp'].dt.to_period('W').astype(str)
            else:
                closed['period'] = closed['timestamp'].dt.to_period('M').astype(str)
            
            grouped = closed.groupby('period').agg({'pnl': ['sum', 'count']}).reset_index()
            grouped.columns = ['period', 'total_pnl', 'trades']
            
            wins = closed[closed['pnl'] > 0].groupby('period').size().reset_index(name='wins')
            grouped = grouped.merge(wins, on='period', how='left').fillna(0)
            grouped['win_rate'] = (grouped['wins'] / grouped['trades'] * 100)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.line(grouped, x='period', y='win_rate', markers=True, title="勝率趨勢")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(grouped, x='period', y='total_pnl', color='total_pnl', 
                            color_continuous_scale='RdYlGn', title="盈虧分布")
                st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(grouped, use_container_width=True)
    else:
        st.info("暫無數據")

# ==================== Tab 4: 風險熱力圖 ====================
with tab4:
    st.header("🔥 風險熱力圖")
    
    trades = load_trades()
    
    if trades:
        df = pd.DataFrame(trades)
        closed = df[df['status'] == 'CLOSED'].copy()
        
        if len(closed) > 0 and 'close_timestamp' in closed.columns:
            closed['close_timestamp'] = pd.to_datetime(closed['close_timestamp'])
            closed['hour'] = closed['close_timestamp'].dt.hour
            closed['weekday'] = closed['close_timestamp'].dt.dayofweek
            
            pivot = closed.pivot_table(values='pnl', index='hour', columns='weekday', aggfunc='sum', fill_value=0)
            
            fig = px.imshow(
                pivot,
                labels=dict(x="星期", y="小時", color="損益"),
                x=['一', '二', '三', '四', '五', '六', '日'],
                y=list(range(24)),
                color_continuous_scale='RdYlGn',
                title="時段損益熱力圖"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.info("💡 綠色 = 盈利時段 | 紅色 = 虧損時段")
        else:
            st.info("暫無足夠數據")
    else:
        st.info("暫無數據")

# ==================== Tab 5: 交易記錄 ====================
with tab5:
    st.header("📜 交易記錄")
    
    trades = load_trades()
    
    if trades:
        df = pd.DataFrame(trades)
        
        col1, col2 = st.columns(2)
        with col1:
            if 'strategy' in df.columns:
                strategy_filter = st.multiselect("策略", df['strategy'].unique(), default=[])
        with col2:
            if 'status' in df.columns:
                status_filter = st.multiselect("狀態", df['status'].unique(), default=[])
        
        filtered = df.copy()
        if strategy_filter:
            filtered = filtered[filtered['strategy'].isin(strategy_filter)]
        if status_filter:
            filtered = filtered[filtered['status'].isin(status_filter)]
        
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("暫無記錄")

# ==================== 頁尾 ====================
st.divider()
st.caption("🤖 技術交易系統 v5.0 | 準確配置版")
st.caption(f"資料庫: {'SQLite ✅' if db else 'JSON'} | 即時更新: {'5秒 ✅' if auto_refresh else '關閉'}")
