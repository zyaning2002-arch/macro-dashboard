import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# 页面基础设置
st.set_page_config(page_title="全球宏观与 BTC 战术看板", layout="wide")
#5分钟时 300000 50分钟时3000000
# 后台静默刷新 (5分钟)·
st_autorefresh(interval=30000, key="macro_board_autorefresh")

# 🎯 核心黑科技：全天候宏观倒计时引擎
def get_market_countdown():
    now_utc = datetime.now(pytz.utc)     
    now_est = now_utc.astimezone(pytz.timezone('America/New_York'))
    
    # 1. 计算 BTC 日线结算倒计时 (下一个 UTC 00:00)
    next_btc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    if now_utc >= next_btc:
        next_btc += timedelta(days=1)
    btc_hours, btc_rem = divmod((next_btc - now_utc).total_seconds(), 3600)
    btc_mins = btc_rem // 60

    # 2. 计算美股开盘倒计时 (下一个 EST 09:30)
    next_us = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    if now_est >= next_us:
        next_us += timedelta(days=1)
    # 智能跳过周末：如果下一个开盘日是周六或周日，自动顺延到周一
    while next_us.weekday() > 4: 
        next_us += timedelta(days=1)
    us_hours, us_rem = divmod((next_us - now_est).total_seconds(), 3600)
    us_mins = us_rem // 60
    
    return f"⏳ **test实战倒计时** ｜ 🪙 **BTC 日线结算**: 还有 `{int(btc_hours)}小时 {int(btc_mins)}分` ｜ 🇺🇸 **华尔街美股开盘**: 还有 `{int(us_hours)}小时 {int(us_mins)}分`"

# 渲染顶部倒计时横幅 (使用显眼的 Info 框)
st.info(get_market_countdown(), icon="⏱️")

# 顶部布局
col_title, col_view, col_btn = st.columns([5, 4, 2])
with col_title:
    st.title("🌐 宏观与 BTC 指挥室")
with col_view:
    st.write("") 
    view_mode = st.radio(
        "视图选择", 
        ["🔥 短线战术 (最近10天)", "🌍 宏观趋势 (最近半年)"], 
        horizontal=True, 
        label_visibility="collapsed"
    )
with col_btn:
    st.write("") 
    if st.button("🔄 手动立即刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("数据来源: Yahoo Finance | 主图: 双均线 | 副图: 成交量 | 自动刷新: 5分钟")

# 核心配置字典
MARKETS = {
    # 【第一排：地缘与大宗】
    "🟡 黄金期货 (Gold)": {"ticker": "GC=F", "ma": [10, 20], "desc": "乱世买黄金，对冲地缘与通胀", "tz": "America/New_York", "tz_name": "纽约"},
    "🛢️ 原油期货 (WTI)": {"ticker": "CL=F", "ma": [10, 20], "desc": "对中东局势敏感，飙升引发通胀", "tz": "America/New_York", "tz_name": "纽约"},
    "🪖 美军工ETF (ITA)": {"ticker": "ITA", "ma": [20, 50], "desc": "军工龙头集合，爆发冲突时飙升", "tz": "America/New_York", "tz_name": "纽约"},

    # 【第二排：加密核心区】
    "🪙 比特币 (BTC)": {"ticker": "BTC-USD", "ma": [7, 30], "desc": "数字黄金，对全球资金面最敏感", "tz": "UTC", "tz_name": "UTC"},
    "💠 以太坊 (ETH)": {"ticker": "ETH-USD", "ma": [7, 30], "desc": "衡量加密市场真实狂热度的风向标", "tz": "UTC", "tz_name": "UTC"},
    "🏢 微策略 (MSTR)": {"ticker": "MSTR", "ma": [20, 50], "desc": "美股BTC杠杆，现货行情的先行指标", "tz": "America/New_York", "tz_name": "纽约"},

    # 【第三排：股市与情绪】
    "🇺🇸 标普500 (^GSPC)": {"ticker": "^GSPC", "ma": [20, 50], "desc": "美国经济基本面，决定宏观牛熊", "tz": "America/New_York", "tz_name": "纽约"},
    "🇺🇸 纳斯达克 (^IXIC)": {"ticker": "^IXIC", "ma": [20, 50], "desc": "与BTC高度联动，受降息预期驱动", "tz": "America/New_York", "tz_name": "纽约"},
    "😨 恐慌指数 (VIX)": {"ticker": "^VIX", "ma": [10, 20], "desc": ">20代表恐慌，暴涨说明华尔街抛售", "tz": "America/New_York", "tz_name": "纽约"},

    # 【第四排：流动性根基】
    "⚓ 10年期美债 (^TNX)": {"ticker": "^TNX", "ma": [20, 50], "desc": "破4.5%则全面抽干风险资产流动性", "tz": "America/New_York", "tz_name": "纽约"},
    "💵 美元指数 (DXY)": {"ticker": "DX-Y.NYB", "ma": [20, 50], "desc": "美元强则BTC弱，资金回流美国标志", "tz": "America/New_York", "tz_name": "纽约"},
    "💣 垃圾债ETF (HYG)": {"ticker": "HYG", "ma": [20, 50], "desc": "暴跌意味资金链断裂，必定带崩BTC", "tz": "America/New_York", "tz_name": "纽约"},

    # 【第五排：中国宏观】
    "🇨🇳 上证指数 (大A)": {"ticker": "000001.SS", "ma": [20, 50], "desc": "反映国内传统经济基本面与央行放水力度", "tz": "Asia/Shanghai", "tz_name": "北京"},
    # 👇 完美替换：华尔街专属的科创50 ETF (KSTR)，数据100%稳定不断更！
    "🚀 科创50 ETF (KSTR)": {"ticker": "KSTR", "ma": [20, 50], "desc": "中国硬科技，外资做多中国科技的通道", "tz": "America/New_York", "tz_name": "纽约"},
    "🇨🇳 人民币汇率 (CNY)": {"ticker": "CNY=X", "ma": [10, 20], "desc": "向上(贬值)外资流出，向下(升值)流入", "tz": "Asia/Shanghai", "tz_name": "北京"}
}

# 1. 获取数据
@st.cache_data(ttl=300) 
def fetch_data(ticker):
    try:
        data = yf.Ticker(ticker).history(period="6mo", interval="1d")
        if data.empty:
            return None
        return data
    except Exception as e:
        return None

# 2. 绘制图表 
def plot_chart(data, title, ma_list, view_mode):
    for ma_days in ma_list:
        data[f'MA_{ma_days}'] = data['Close'].rolling(window=ma_days).mean()
        
    if "10天" in view_mode:
        plot_data = data.tail(10).copy()
    else:
        plot_data = data.copy()
        
    current_time = pd.Timestamp.now(tz=plot_data.index.tz)
    last_record_time = plot_data.index[-1]
    
    end_time = max(current_time, last_record_time) + pd.Timedelta(hours=12)
    start_time = plot_data.index[0] - pd.Timedelta(hours=12)
    
    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(
        x=plot_data.index, open=plot_data['Open'], high=plot_data['High'],
        low=plot_data['Low'], close=plot_data['Close'], name="K线",
        increasing_line_color='red', decreasing_line_color='green', showlegend=False
    ), row=1, col=1)
    
    colors = ['#1f77b4', '#ff7f0e']
    for i, ma_days in enumerate(ma_list):
        fig.add_trace(go.Scatter(
            x=plot_data.index, y=plot_data[f'MA_{ma_days}'], 
            line=dict(color=colors[i % 2], width=1.5), name=f'{ma_days}日均线'
        ), row=1, col=1)

    if 'Volume' in plot_data.columns:
        vol_colors = ['red' if row['Close'] >= row['Open'] else 'green' for index, row in plot_data.iterrows()]
        fig.add_trace(go.Bar(
            x=plot_data.index, y=plot_data['Volume'], marker_color=vol_colors, 
            name='成交量', showlegend=False
        ), row=2, col=1)

    fig.update_layout(
        margin=dict(l=0, r=0, t=20, b=0),
        height=260, 
        xaxis_rangeslider_visible=False, 
        xaxis2_rangeslider_visible=False, 
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_xaxes(range=[start_str, end_str], type="date")
    return fig

# 3. 页面渲染
cols = st.columns(3)
for index, (name, config) in enumerate(MARKETS.items()):
    col = cols[index % 3]
    with col:
        st.subheader(name)
        
        tz_obj = pytz.timezone(config["tz"])
        local_time_str = datetime.now(tz_obj).strftime('%m-%d %H:%M')
        st.caption(f"💡 {config['desc']} | 🕒 **{config['tz_name']}: {local_time_str}**")
        
        data = fetch_data(config["ticker"])
        
        if data is not None and len(data) >= 2:
            current_price = data['Close'].iloc[-1]
            previous_price = data['Close'].iloc[-2]
            change_val = current_price - previous_price
            change_pct = (change_val / previous_price) * 100
            last_trade_date = data.index[-1].strftime('%Y-%m-%d')
            
            st.metric(
                label=f"最新价格 (截至交易日: {last_trade_date})", 
                value=f"{current_price:.2f}", 
                delta=f"{change_val:.2f} ({change_pct:.2f}%)"
            )
            
            st.plotly_chart(plot_chart(data, name, config["ma"], view_mode), use_container_width=True)
        else:
            st.warning("数据抓取中或接口受限...")
        
        st.markdown("---")