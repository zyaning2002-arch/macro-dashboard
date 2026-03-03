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
# 0. 🎛️ 绝对时间轴引擎 (彻底解决漂移)
# ==========================================
GLOBAL_REFRESH_SEC = 15
YAHOO_INTERVAL_SEC = 120

now_epoch = int(time.time())
okx_window = now_epoch // GLOBAL_REFRESH_SEC
yahoo_window = now_epoch // YAHOO_INTERVAL_SEC

global_target_epoch = (okx_window + 1) * GLOBAL_REFRESH_SEC
yahoo_target_epoch = (yahoo_window + 1) * YAHOO_INTERVAL_SEC

# ==========================================
# 1. 🚀 页面深度优化
# ==========================================
st.set_page_config(page_title="全球宏观与 BTC 战术看板", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.9rem !important; }
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .market-desc { font-size: 0.8rem; color: #888; margin-top: -10px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=GLOBAL_REFRESH_SEC * 1000, key="macro_board_heartbeat")

# ==========================================
# 2. 🌍 全球时钟
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

# ==========================================
# 3. 核心行情字典 (完美 18 宫格：15个原指标 + 3个战术指标)
# ==========================================
MARKETS = {
    # 第一排：避险与大宗
    "🟡 黄金期货 (Gold)": {"ticker": "GC=F", "source": "yahoo", "ma": [10, 20], "desc": "乱世避险买黄金，对冲地缘与通胀", "tz": "America/New_York", "tz_name": "纽约"},
    "🛢️ 原油期货 (WTI)": {"ticker": "CL=F", "source": "yahoo", "ma": [10, 20], "desc": "对中东局势极度敏感，飙升引发通胀交易", "tz": "America/New_York", "tz_name": "纽约"},
    "🪖 美军工ETF (ITA)": {"ticker": "ITA", "source": "yahoo", "ma": [20, 50], "desc": "军工龙头集合，爆发局部冲突时逆势飙升", "tz": "America/New_York", "tz_name": "纽约"},
    
    # 第二排：加密核心与美股投影 (全员回归！)
    "🪙 比特币 (BTC)": {"ticker": "BTC-USDT", "source": "okx", "ma": [7, 30], "desc": "数字黄金，全球流动性扩张的终极蓄水池", "tz": "UTC", "tz_name": "UTC"},
    "💠 以太坊 (ETH)": {"ticker": "ETH-USDT", "source": "okx", "ma": [7, 30], "desc": "币圈风向标，反映链上生态的真实活跃度", "tz": "UTC", "tz_name": "UTC"},
    "🏢 微策略 (MSTR)": {"ticker": "MSTR", "source": "yahoo", "ma": [20, 50], "desc": "美股BTC杠杆，现货行情的高敏先行指标", "tz": "America/New_York", "tz_name": "纽约"},

    # 第三排：周末增量雷达区 (BTC专精辅助)
    "⚖️ ETH/BTC 汇率": {"ticker": "ETH-BTC", "source": "okx", "ma": [7, 30], "desc": "【资金跷跷板】上升代表全市场山寨看多情绪", "tz": "UTC", "tz_name": "UTC"},
    "💵 稳定币场外溢价": {"ticker": "USDC-USDT", "source": "okx", "ma": [7, 30], "desc": "【入场雷达】>1代表场外买盘/亚洲资金正在进场", "tz": "UTC", "tz_name": "UTC"},
    "🏛️ Coinbase (COIN)": {"ticker": "COIN", "source": "yahoo", "ma": [20, 50], "desc": "美国正规军入口，华尔街主力买卖意愿投影", "tz": "America/New_York", "tz_name": "纽约"},

    # 第四排：股市与机构情绪 (VIX 回归！)
    "🇺🇸 标普500 (^GSPC)": {"ticker": "^GSPC", "source": "yahoo", "ma": [20, 50], "desc": "美国经济基本面，决定宏观牛熊大方向", "tz": "America/New_York", "tz_name": "纽约"},
    "🇺🇸 纳斯达克 (^IXIC)": {"ticker": "^IXIC", "source": "yahoo", "ma": [20, 50], "desc": "与BTC高度联动，受科技股与降息预期驱动", "tz": "America/New_York", "tz_name": "纽约"},
    "😨 恐慌指数 (VIX)": {"ticker": "^VIX", "source": "yahoo", "ma": [10, 20], "desc": ">20代表恐慌，暴涨说明华尔街大举抛售", "tz": "America/New_York", "tz_name": "纽约"},

    # 第五排：宏观流动性根基
    "⚓ 10年期美债 (^TNX)": {"ticker": "^TNX", "source": "yahoo", "ma": [20, 50], "desc": "无风险利率标杆，破4.5%则全面抽干风险资产", "tz": "America/New_York", "tz_name": "纽约"},
    "💵 美元指数 (DXY)": {"ticker": "DX-Y.NYB", "source": "yahoo", "ma": [20, 50], "desc": "美元强则BTC弱，反映全球资金回流美国本土", "tz": "America/New_York", "tz_name": "纽约"},
    "💣 垃圾债ETF (HYG)": {"ticker": "HYG", "source": "yahoo", "ma": [20, 50], "desc": "企业流动性指标，暴跌意味资金链断裂带崩BTC", "tz": "America/New_York", "tz_name": "纽约"},

    # 第六排：中国宏观
    "🇨🇳 上证指数 (大A)": {"ticker": "000001.SS", "source": "yahoo", "ma": [20, 50], "desc": "反映国内传统经济基本面与央行放水力度", "tz": "Asia/Shanghai", "tz_name": "北京"},
    "🚀 科创50 ETF (KSTR)": {"ticker": "KSTR", "source": "yahoo", "ma": [20, 50], "desc": "【新质生产力】华尔街外资做多中国科技通道", "tz": "America/New_York", "tz_name": "纽约"},
    "🇨🇳 人民币汇率 (CNY)": {"ticker": "CNY=X", "source": "yahoo", "ma": [10, 20], "desc": "向上(贬值)外资流出，向下(升值)热钱流入", "tz": "Asia/Shanghai", "tz_name": "北京"}
}

# ==========================================
# 4. 绝对时间窗口数据引擎
# ==========================================
@st.cache_data(max_entries=20) 
def fetch_okx_data(ticker, window):
    try:
        url = f"https://www.okx.com/api/v5/market/candles?instId={ticker}&bar=1D&limit=100"
        resp = requests.get(url, timeout=5).json()
        if resp['code'] == '0':
            df = pd.DataFrame(resp['data'], columns=['ts', 'Open', 'High', 'Low', 'Close', 'Volume', 'volCcy', 'volCcyQuote', 'confirm'])
            df.index = pd.to_datetime(pd.to_numeric(df['ts']), unit='ms', utc=True)
            df = df.sort_index()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']: df[col] = pd.to_numeric(df[col])
            return df
        return None
    except: return None

@st.cache_data(max_entries=30) 
def fetch_yahoo_data(ticker, window):
    try:
        data = yf.Ticker(ticker).history(period="6mo", interval="1d")
        return data if not data.empty else None
    except: return None

# ==========================================
# 5. UI 顶栏
# ==========================================
col_title, col_view, col_btn = st.columns([3, 5, 2])
with col_title:
    st.markdown(f"### 🌐 宏观指挥室")
with col_view:
    view_mode = st.radio("视图", ["🔥 短线", "🌍 宏观", "📱 极简"], horizontal=True, label_visibility="collapsed")
with col_btn:
    if st.button("🔄 手动强制刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

components.html(
    f"""
    <style>
        .status-bar {{ font-family: sans-serif; font-size: 13px; display: flex; justify-content: space-between; background: #111; color: #10B981; padding: 10px 15px; border-radius: 8px; border: 1px solid #333; }}
        @media (max-width: 600px) {{ .status-bar {{ flex-direction: column; text-align: center; gap: 8px; padding: 10px; }} }}
    </style>
    <div class="status-bar">
        <div>🚀 OKX 直连极速: <span id="g_t">--</span> s</div>
        <div>🌍 Yahoo 宏观防封: <span id="y_t">--</span> s</div>
    </div>
    <script>
        var g_ms = {global_target_epoch} * 1000;
        var y_ms = {yahoo_target_epoch} * 1000;
        
        setInterval(function(){{
            var now = Date.now();
            document.getElementById("g_t").innerHTML = Math.max(0, Math.ceil((g_ms - now)/1000));
            document.getElementById("y_t").innerHTML = Math.max(0, Math.ceil((y_ms - now)/1000));
        }}, 200);
    </script>
    """, height=75
)

# ==========================================
# 6. 图表绘制 (Hover 纯净版)
# ==========================================
def plot_chart(data, ma_list, view_mode, target_tz):
    plot_data = data.copy()
    if plot_data.index.tz is None: plot_data.index = plot_data.index.tz_localize('UTC')
    plot_data.index = plot_data.index.tz_convert(target_tz).tz_localize(None)
    
    for ma in ma_list: plot_data[f'MA{ma}'] = plot_data['Close'].rolling(window=ma).mean()
    if "短线" in view_mode or "极简" in view_mode: plot_data = plot_data.tail(15)
        
    chart_height = 180 if "极简" in view_mode else 220
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(
        x=plot_data.index, open=plot_data['Open'], high=plot_data['High'], low=plot_data['Low'], close=plot_data['Close'], 
        name="K线", increasing_line_color='#26A69A', decreasing_line_color='#EF5350', showlegend=False
    ), row=1, col=1)
    
    for i, ma in enumerate(ma_list):
        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data[f'MA{ma}'], line=dict(width=1), name=f'MA{ma}', hoverinfo='skip'), row=1, col=1)

    if 'Volume' in plot_data.columns:
        vol_colors = ['#26A69A' if r['Close'] >= r['Open'] else '#EF5350' for i, r in plot_data.iterrows()]
        fig.add_trace(go.Bar(x=plot_data.index, y=plot_data['Volume'], marker_color=vol_colors, showlegend=False, hoverinfo='skip'), row=2, col=1)

    fig.update_layout(margin=dict(l=5, r=5, t=5, b=5), height=chart_height, xaxis_rangeslider_visible=False, 
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_layout(hovermode="x unified")
    return fig

# ==========================================
# 7. 渲染逻辑 (携带时间窗口拉取，包含稳定币反转魔法)
# ==========================================
display_cols = 1 if "极简" in view_mode else 3
cols = st.columns(display_cols)

for index, (name, config) in enumerate(MARKETS.items()):
    with cols[index % display_cols]:
        if config["source"] == "okx":
            data = fetch_okx_data(config["ticker"], okx_window)
        else:
            data = fetch_yahoo_data(config["ticker"], yahoo_window)
        
        if data is not None and len(data) >= 2:
            
            # 💡 核心魔法：如果是 USDC-USDT，克隆数据并将所有价格取倒数，完美合成为你想要的 USDT 溢价视角！
            if config["ticker"] == "USDC-USDT":
                data = data.copy()
                for col in ['Open', 'High', 'Low', 'Close']:
                    data[col] = 1 / data[col]
                # 倒数之后，原来的最高价会变成最低价，所以需要互换 High 和 Low
                data['High'], data['Low'] = data['Low'].copy(), data['High'].copy()

            curr = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            diff = curr - prev
            pct = (diff / prev) * 100
            
            local_time = datetime.now(pytz.timezone(config['tz'])).strftime('%m-%d %H:%M')
            
            st.write(f"**{name}**")
            st.markdown(f"<div class='market-desc'>💡 {config['desc']} | 🕒 {config['tz_name']}: {local_time}</div>", unsafe_allow_html=True)
            
            # 这里的判断条件也要改成 USDC-USDT，保证稳定币显示 4 位小数
            if config["ticker"] in ["USDC-USDT", "ETH-BTC"]:
                st.metric(label="", value=f"{curr:.4f}", delta=f"{diff:.4f} ({pct:.2f}%)", label_visibility="collapsed")
            else:
                st.metric(label="", value=f"{curr:.2f}", delta=f"{diff:.2f} ({pct:.2f}%)", label_visibility="collapsed")
                
            st.plotly_chart(plot_chart(data, config["ma"], view_mode, config["tz"]), use_container_width=True, config={'displayModeBar': False})
        else:
            st.error(f"{name} 获取失败")
        st.divider()