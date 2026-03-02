import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz
import time
import requests
import streamlit.components.v1 as components

# ==========================================
# 0. 🎛️ 全局核心控制台
# ==========================================
CONFIG = {
    "GLOBAL_REFRESH_SEC": 15,    # 网页整体心跳与前端刷新周期 (秒)
    "OKX_CACHE_SEC": 10,         # 必须小于15！确保每次15秒刷新时必定穿透去拿新数据
    "YAHOO_CACHE_SEC": 115       # 必须小于120！保证第8次刷新(120秒)时必定穿透
}

# ==========================================
# 1. 页面基础设置与全局心跳
# ==========================================
st.set_page_config(page_title="全球宏观与 BTC 战术看板", layout="wide")
st_autorefresh(interval=CONFIG["GLOBAL_REFRESH_SEC"] * 1000, key="macro_board_autorefresh")

# 🧠 核心机制：为雅虎倒计时开启“跨页面长期记忆”
now_epoch = time.time()
if "yahoo_target_epoch" not in st.session_state or now_epoch >= st.session_state.yahoo_target_epoch:
    st.session_state.yahoo_target_epoch = now_epoch + CONFIG["YAHOO_CACHE_SEC"]

# 计算两个引擎绝对的过期时间戳
global_target_epoch = now_epoch + CONFIG["GLOBAL_REFRESH_SEC"]
yahoo_target_epoch = st.session_state.yahoo_target_epoch

# ==========================================
# 2. 核心数据字典
# ==========================================
MARKETS = {
    "🟡 黄金期货 (Gold)": {"ticker": "GC=F", "source": "yahoo", "ma": [10, 20], "desc": "乱世买黄金，对冲地缘与通胀", "tz": "America/New_York", "tz_name": "纽约"},
    "🛢️ 原油期货 (WTI)": {"ticker": "CL=F", "source": "yahoo", "ma": [10, 20], "desc": "对中东局势敏感，飙升引发通胀", "tz": "America/New_York", "tz_name": "纽约"},
    "🪖 美军工ETF (ITA)": {"ticker": "ITA", "source": "yahoo", "ma": [20, 50], "desc": "军工龙头集合，爆发冲突时飙升", "tz": "America/New_York", "tz_name": "纽约"},
    "🪙 比特币 (BTC)": {"ticker": "BTC-USDT", "source": "okx", "ma": [7, 30], "desc": "【直连OKX】零延迟实时行情", "tz": "UTC", "tz_name": "UTC"},
    "💠 以太坊 (ETH)": {"ticker": "ETH-USDT", "source": "okx", "ma": [7, 30], "desc": "【直连OKX】精确同步交易所", "tz": "UTC", "tz_name": "UTC"},
    "🏢 微策略 (MSTR)": {"ticker": "MSTR", "source": "yahoo", "ma": [20, 50], "desc": "美股BTC杠杆，现货行情的先行指标", "tz": "America/New_York", "tz_name": "纽约"},
    "🇺🇸 标普500 (^GSPC)": {"ticker": "^GSPC", "source": "yahoo", "ma": [20, 50], "desc": "美国经济基本面，决定宏观牛熊", "tz": "America/New_York", "tz_name": "纽约"},
    "🇺🇸 纳斯达克 (^IXIC)": {"ticker": "^IXIC", "source": "yahoo", "ma": [20, 50], "desc": "与BTC高度联动，受降息预期驱动", "tz": "America/New_York", "tz_name": "纽约"},
    "😨 恐慌指数 (VIX)": {"ticker": "^VIX", "source": "yahoo", "ma": [10, 20], "desc": ">20代表恐慌，暴涨说明华尔街抛售", "tz": "America/New_York", "tz_name": "纽约"},
    "⚓ 10年期美债 (^TNX)": {"ticker": "^TNX", "source": "yahoo", "ma": [20, 50], "desc": "破4.5%则全面抽干风险资产流动性", "tz": "America/New_York", "tz_name": "纽约"},
    "💵 美元指数 (DXY)": {"ticker": "DX-Y.NYB", "source": "yahoo", "ma": [20, 50], "desc": "美元强则BTC弱，资金回流美国标志", "tz": "America/New_York", "tz_name": "纽约"},
    "💣 垃圾债ETF (HYG)": {"ticker": "HYG", "source": "yahoo", "ma": [20, 50], "desc": "暴跌意味资金链断裂，必定带崩BTC", "tz": "America/New_York", "tz_name": "纽约"},
    "🇨🇳 上证指数 (大A)": {"ticker": "000001.SS", "source": "yahoo", "ma": [20, 50], "desc": "反映国内传统经济基本面与央行放水", "tz": "Asia/Shanghai", "tz_name": "北京"},
    "🚀 科创50 ETF (KSTR)": {"ticker": "KSTR", "source": "yahoo", "ma": [20, 50], "desc": "【新质生产力】华尔街做多中国科技", "tz": "America/New_York", "tz_name": "纽约"},
    "🇨🇳 人民币汇率 (CNY)": {"ticker": "CNY=X", "source": "yahoo", "ma": [10, 20], "desc": "向上(贬值)外资流出，向下(升值)流入", "tz": "Asia/Shanghai", "tz_name": "北京"}
}

# ==========================================
# 3. 异步双通道数据抓取引擎
# ==========================================
@st.cache_data(ttl=CONFIG["OKX_CACHE_SEC"])  # 👈 就是把这里括号里面的名字改掉
def fetch_okx_data(ticker):
    try:
        url = f"https://www.okx.com/api/v5/market/candles?instId={ticker}&bar=1D&limit=180"
        resp = requests.get(url, timeout=5).json()
        if resp['code'] == '0':
            data = resp['data']
            df = pd.DataFrame(data, columns=['ts', 'Open', 'High', 'Low', 'Close', 'Volume', 'volCcy', 'volCcyQuote', 'confirm'])
            df['ts'] = pd.to_numeric(df['ts'])
            df.index = pd.to_datetime(df['ts'], unit='ms', utc=True)
            df = df.sort_index() 
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col])
            return df
        return None
    except Exception:
        return None

@st.cache_data(ttl=CONFIG["YAHOO_CACHE_SEC"]) 
def fetch_yahoo_data(ticker):
    try:
        data = yf.Ticker(ticker).history(period="6mo", interval="1d")
        if data.empty: return None
        return data
    except Exception:
        return None

# ==========================================
# 4. 顶部时钟与 UI 布局
# ==========================================
def get_global_clocks_and_countdown():
    now_utc = datetime.now(pytz.utc)
    now_est = now_utc.astimezone(pytz.timezone('America/New_York'))
    now_sh = now_utc.astimezone(pytz.timezone('Asia/Shanghai'))
    
    clock_str = f"🕒 **全球时钟** ｜ 🇨🇳 北京: `{now_sh.strftime('%H:%M')}` ｜ 🇺🇸 纽约: `{now_est.strftime('%H:%M')}` ｜ 🌐 UTC: `{now_utc.strftime('%H:%M')}`"
    
    next_btc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    if now_utc >= next_btc: next_btc += timedelta(days=1)
    btc_hours, btc_rem = divmod((next_btc - now_utc).total_seconds(), 3600)
    
    next_us = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    if now_est >= next_us: next_us += timedelta(days=1)
    while next_us.weekday() > 4: next_us += timedelta(days=1)
    us_hours, us_rem = divmod((next_us - now_est).total_seconds(), 3600)
    
    countdown_str = f"⏳ **实战倒计时** ｜ 🪙 **BTC 日结**: 还有 `{int(btc_hours)}时 {int(btc_rem // 60)}分` ｜ 🇺🇸 **美股开盘**: 还有 `{int(us_hours)}时 {int(us_rem // 60)}分`"
    return clock_str + "  \n" + countdown_str

st.info(get_global_clocks_and_countdown())

col_title, col_view, col_btn = st.columns([3, 5, 2])
with col_title: st.title("🌐 宏观指挥室")
with col_view:
    st.write("") 
    view_mode = st.radio("视图选择", ["🔥 短线 (10天)", "🌍 宏观 (半年)", "📱 手机极简模式"], horizontal=True, label_visibility="collapsed")
with col_btn:
    st.write("") 
    if st.button("🔄 手动强制刷新", use_container_width=True):
        st.cache_data.clear()
        st.session_state.yahoo_target_epoch = time.time() + CONFIG["YAHOO_CACHE_SEC"] # 手动刷新连雅虎时钟一起重置
        st.rerun()

# 🎯 物理级绝对时间双引擎校准 (彻底告别漂移！)
components.html(
    f"""
    <style>
        .footer-info {{ color: #555; font-family: sans-serif; font-size: 13px; display: flex; justify-content: space-between; align-items: center; background: rgba(16, 185, 129, 0.1); padding: 8px 15px; border-radius: 8px; border-left: 4px solid #10B981; margin-bottom: 10px;}}
        .timer-box {{ display: flex; gap: 20px; }}
        .highlight {{ color: #10B981; font-weight: bold; font-size: 14px;}}
        @media (max-width: 600px) {{ .footer-info {{ flex-direction: column; gap: 8px; text-align: center; }} .timer-box {{ flex-direction: column; gap: 4px; }} }}
    </style>
    
    <div class="footer-info">
        <div>📡 数据通道状态：OKX 直连极速模式 / Yahoo 宏观防封模式</div>
        <div class="timer-box">
            <div>🚀 OKX 刷新: <span id="global_timer" class="highlight">检测中...</span></div>
            <div>🌍 Yahoo 刷新: <span id="yahoo_timer" class="highlight">检测中...</span></div>
        </div>
    </div>
    
    <script>
        // 将 Python 传过来的精确绝对过期时间，转换成 JS 的毫秒
        var globalTargetMs = {global_target_epoch} * 1000;
        var yahooTargetMs = {yahoo_target_epoch} * 1000;

        // 每 0.2 秒去向现实物理时间对表一次！
        setInterval(function(){{
            var now = Date.now();
            var globalLeft = Math.ceil((globalTargetMs - now) / 1000);
            var yahooLeft = Math.ceil((yahooTargetMs - now) / 1000);

            var globalElem = document.getElementById("global_timer");
            if(globalLeft > 0) {{
                globalElem.innerHTML = globalLeft + " 秒";
            }} else {{
                globalElem.innerHTML = "⚡ 同步中...";
            }}

            var yahooElem = document.getElementById("yahoo_timer");
            if(yahooLeft > 0) {{
                yahooElem.innerHTML = yahooLeft + " 秒";
            }} else {{
                yahooElem.innerHTML = "⚡ 同步中...";
            }}
        }}, 200); 
    </script>
    """,
    height=60
)

# ==========================================
# 5. 图表绘制模块 (绿涨红跌)
# ==========================================
def plot_chart(data, title, ma_list, view_mode):
    for ma_days in ma_list: data[f'MA_{ma_days}'] = data['Close'].rolling(window=ma_days).mean()
    plot_data = data.tail(10).copy() if "10天" in view_mode else data.copy()
        
    end_time = max(pd.Timestamp.now(tz=plot_data.index.tz), plot_data.index[-1]) + pd.Timedelta(hours=12)
    start_time = plot_data.index[0] - pd.Timedelta(hours=12)
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(
        x=plot_data.index, open=plot_data['Open'], high=plot_data['High'], low=plot_data['Low'], close=plot_data['Close'], 
        name="K线", increasing_line_color='#26A69A', decreasing_line_color='#EF5350', showlegend=False
    ), row=1, col=1)
    
    colors = ['#1f77b4', '#ff7f0e']
    for i, ma_days in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data[f'MA_{ma_days}'], line=dict(color=colors[i % 2], width=1.5), name=f'{ma_days}日均线'), row=1, col=1)

    if 'Volume' in plot_data.columns:
        vol_colors = ['#26A69A' if row['Close'] >= row['Open'] else '#EF5350' for index, row in plot_data.iterrows()]
        fig.add_trace(go.Bar(x=plot_data.index, y=plot_data['Volume'], marker_color=vol_colors, name='成交量', showlegend=False), row=2, col=1)

    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=260, xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_xaxes(range=[start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S')], type="date")
    return fig

# ==========================================
# 6. 页面渲染分发机制
# ==========================================
if "手机" in view_mode:
    st.markdown("---")
    for name, config in MARKETS.items():
        st.subheader(name)
        st.caption(f"💡 {config['desc']} | 🕒 **{config['tz_name']}: {datetime.now(pytz.timezone(config['tz'])).strftime('%m-%d %H:%M')}**")
        data = fetch_okx_data(config["ticker"]) if config.get("source", "yahoo") == "okx" else fetch_yahoo_data(config["ticker"])
        if data is not None and len(data) >= 2:
            st.metric(label="最新价格", value=f"{data['Close'].iloc[-1]:.2f}", delta=f"{(data['Close'].iloc[-1] - data['Close'].iloc[-2]):.2f} ({((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100):.2f}%)")
        else: st.warning("数据抓取中或接口受限...")
        st.markdown("---")
else:
    cols = st.columns(3)
    for index, (name, config) in enumerate(MARKETS.items()):
        with cols[index % 3]:
            st.subheader(name)
            st.caption(f"💡 {config['desc']} | 🕒 **{config['tz_name']}: {datetime.now(pytz.timezone(config['tz'])).strftime('%m-%d %H:%M')}**")
            data = fetch_okx_data(config["ticker"]) if config.get("source", "yahoo") == "okx" else fetch_yahoo_data(config["ticker"])
            if data is not None and len(data) >= 2:
                st.metric(label=f"最新价 (截至: {data.index[-1].strftime('%Y-%m-%d')})", value=f"{data['Close'].iloc[-1]:.2f}", delta=f"{(data['Close'].iloc[-1] - data['Close'].iloc[-2]):.2f} ({((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100):.2f}%)")
                st.plotly_chart(plot_chart(data, name, config["ma"], view_mode), use_container_width=True)
            else: st.warning("数据抓取中或接口受限...")
            st.markdown("---")