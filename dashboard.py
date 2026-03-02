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

# 页面基础设置
st.set_page_config(page_title="全球宏观与 BTC 战术看板", layout="wide")

# 后台静默刷新 (30秒)
st_autorefresh(interval=30000, key="macro_board_autorefresh")

# 🎯 核心黑科技 1：全球三大时钟与宏观倒计时双引擎
def get_global_clocks_and_countdown():
    now_utc = datetime.now(pytz.utc)
    now_est = now_utc.astimezone(pytz.timezone('America/New_York'))
    now_sh = now_utc.astimezone(pytz.timezone('Asia/Shanghai'))
    
    # 🌍 生成全球时钟字符串
    clock_str = f"🕒 **全球时钟** ｜ 🇨🇳 北京: `{now_sh.strftime('%H:%M')}` ｜ 🇺🇸 纽约: `{now_est.strftime('%H:%M')}` ｜ 🌐 UTC: `{now_utc.strftime('%H:%M')}`"
    
    # ⏳ 计算 BTC 日线结算倒计时 (下一个 UTC 00:00)
    next_btc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    if now_utc >= next_btc:
        next_btc += timedelta(days=1)
    btc_hours, btc_rem = divmod((next_btc - now_utc).total_seconds(), 3600)
    btc_mins = btc_rem // 60

    # ⏳ 计算美股开盘倒计时 (下一个 EST 09:30)
    next_us = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    if now_est >= next_us:
        next_us += timedelta(days=1)
    while next_us.weekday() > 4: 
        next_us += timedelta(days=1)
    us_hours, us_rem = divmod((next_us - now_est).total_seconds(), 3600)
    us_mins = us_rem // 60
    
    countdown_str = f"⏳ **实战倒计时** ｜ 🪙 **BTC 日结**: 还有 `{int(btc_hours)}时 {int(btc_mins)}分` ｜ 🇺🇸 **美股开盘**: 还有 `{int(us_hours)}时 {int(us_mins)}分`"
    
    # 将时钟和倒计时分两行显示
    return clock_str + "  \n" + countdown_str

# 渲染顶部信息栏
st.info(get_global_clocks_and_countdown())

# 顶部布局升级：加入手机极简模式
col_title, col_view, col_btn = st.columns([3, 5, 2])
with col_title:
    st.title("🌐 宏观指挥室")
with col_view:
    st.write("") 
    view_mode = st.radio(
        "视图选择", 
        ["🔥 短线 (10天)", "🌍 宏观 (半年)", "📱 手机极简模式"], 
        horizontal=True, 
        label_visibility="collapsed"
    )
with col_btn:
    st.write("") 
    if st.button("🔄 手动刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

import streamlit.components.v1 as components

# 植入前端 Javascript 实现无感丝滑倒计时 (完美适配手机与电脑端)
components.html(
    f"""
    <style>
        .footer-info {{
            color: #888; 
            font-family: sans-serif; 
            font-size: 14px; 
            display: flex; 
            justify-content: space-between;
            align-items: center;
        }}
        /* 📱 响应式魔法：当屏幕宽度小于 600px（手机）时，自动变成上下两行 */
        @media (max-width: 600px) {{
            .footer-info {{
                flex-direction: column;
                justify-content: center;
                font-size: 12px;
                gap: 5px;
            }}
        }}
    </style>
    
    <div class="footer-info">
        <div>数据来源: Yahoo Finance | 主图: 双均线 | 副图: 成交量</div>
        <div id="status_text">🔄 距离下次获取新数据: <span style="color: #ff4b4b; font-weight: bold;">30</span> 秒</div>
    </div>
    
    <script>
        // 动态时间戳，强制前端每次感知 Python 的刷新动作: {time.time()}
        var timeleft = 30;
        var statusText = document.getElementById("status_text");
        
        var downloadTimer = setInterval(function(){{
            timeleft -= 1;
            if(timeleft > 0){{
                statusText.innerHTML = "🔄 距离下次刷新还有: <span style='color: #ff4b4b; font-weight: bold;'>" + timeleft + "</span> 秒";
            }} else {{
                statusText.innerHTML = "<span style='color: #ff4b4b; font-weight: bold;'>⚡ 正在从雅虎财经同步最新价格...</span>";
                
                // 智能兜底机制
                if(timeleft <= -5){{
                    timeleft = 30;
                }}
            }}
        }}, 1000);
    </script>
    """,
    height=45  # 👈 这里把高度从 30 调到了 45，保证手机端换行后不会被切掉！
)

# 核心配置字典 (注意看 BTC 和 ETH 的 ticker 变成了 OKX 的交易对格式，并加了 source 标签)
MARKETS = {
    # 第一排：地缘与大宗 (保持雅虎)
    "🟡 黄金期货 (Gold)": {"ticker": "GC=F", "source": "yahoo", "ma": [10, 20], "desc": "乱世买黄金，对冲地缘与通胀", "tz": "America/New_York", "tz_name": "纽约"},
    "🛢️ 原油期货 (WTI)": {"ticker": "CL=F", "source": "yahoo", "ma": [10, 20], "desc": "对中东局势敏感，飙升引发通胀", "tz": "America/New_York", "tz_name": "纽约"},
    "🪖 美军工ETF (ITA)": {"ticker": "ITA", "source": "yahoo", "ma": [20, 50], "desc": "军工龙头集合，爆发冲突时飙升", "tz": "America/New_York", "tz_name": "纽约"},

    # 🚀 第二排：加密核心区 (直连 OKX 零延迟通道！)
    "🪙 比特币 (BTC)": {"ticker": "BTC-USDT", "source": "okx", "ma": [7, 30], "desc": "【直连 OKX】零延迟实时行情", "tz": "UTC", "tz_name": "UTC"},
    "💠 以太坊 (ETH)": {"ticker": "ETH-USDT", "source": "okx", "ma": [7, 30], "desc": "【直连 OKX】精确同步交易所", "tz": "UTC", "tz_name": "UTC"},
    "🏢 微策略 (MSTR)": {"ticker": "MSTR", "source": "yahoo", "ma": [20, 50], "desc": "美股BTC杠杆，现货行情的先行指标", "tz": "America/New_York", "tz_name": "纽约"},

    # 第三排：股市与情绪 (保持雅虎)
    "🇺🇸 标普500 (^GSPC)": {"ticker": "^GSPC", "source": "yahoo", "ma": [20, 50], "desc": "美国经济基本面，决定宏观牛熊", "tz": "America/New_York", "tz_name": "纽约"},
    "🇺🇸 纳斯达克 (^IXIC)": {"ticker": "^IXIC", "source": "yahoo", "ma": [20, 50], "desc": "与BTC高度联动，受降息预期驱动", "tz": "America/New_York", "tz_name": "纽约"},
    "😨 恐慌指数 (VIX)": {"ticker": "^VIX", "source": "yahoo", "ma": [10, 20], "desc": ">20代表恐慌，暴涨说明华尔街抛售", "tz": "America/New_York", "tz_name": "纽约"},

    # 第四排：流动性根基 (保持雅虎)
    "⚓ 10年期美债 (^TNX)": {"ticker": "^TNX", "source": "yahoo", "ma": [20, 50], "desc": "破4.5%则全面抽干风险资产流动性", "tz": "America/New_York", "tz_name": "纽约"},
    "💵 美元指数 (DXY)": {"ticker": "DX-Y.NYB", "source": "yahoo", "ma": [20, 50], "desc": "美元强则BTC弱，资金回流美国标志", "tz": "America/New_York", "tz_name": "纽约"},
    "💣 垃圾债ETF (HYG)": {"ticker": "HYG", "source": "yahoo", "ma": [20, 50], "desc": "暴跌意味资金链断裂，必定带崩BTC", "tz": "America/New_York", "tz_name": "纽约"},

    # 第五排：中国宏观 (保持雅虎)
    "🇨🇳 上证指数 (大A)": {"ticker": "000001.SS", "source": "yahoo", "ma": [20, 50], "desc": "反映国内传统经济基本面与央行放水", "tz": "Asia/Shanghai", "tz_name": "北京"},
    "🚀 科创50 ETF (KSTR)": {"ticker": "KSTR", "source": "yahoo", "ma": [20, 50], "desc": "【新质生产力】华尔街做多中国科技通道", "tz": "America/New_York", "tz_name": "纽约"},
    "🇨🇳 人民币汇率 (CNY)": {"ticker": "CNY=X", "source": "yahoo", "ma": [10, 20], "desc": "向上(贬值)外资流出，向下(升值)流入", "tz": "Asia/Shanghai", "tz_name": "北京"}
}

# 🎯 智能数据抓取引擎：根据 source 标签自动切换数据源
@st.cache_data(ttl=10) 
def fetch_data(ticker, source="yahoo"):
    try:
        # 🟢 OKX 高速通道
        if source == "okx":
            url = f"https://www.okx.com/api/v5/market/candles?instId={ticker}&bar=1D&limit=180"
            resp = requests.get(url).json()
            if resp['code'] == '0':
                data = resp['data']
                # OKX返回格式：[ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                df = pd.DataFrame(data, columns=['ts', 'Open', 'High', 'Low', 'Close', 'Volume', 'volCcy', 'volCcyQuote', 'confirm'])
                df['ts'] = pd.to_numeric(df['ts'])
                df.index = pd.to_datetime(df['ts'], unit='ms', utc=True)
                df = df.sort_index() # OKX默认是倒序，画图需要正序
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = pd.to_numeric(df[col])
                return df
            return None
            
        # 🔵 雅虎常规通道
        else:
            data = yf.Ticker(ticker).history(period="6mo", interval="1d")
            if data.empty:
                return None
            return data
    except Exception as e:
        return None

# ==================== (下方是你原来的 def plot_chart 和页面渲染分流机制代码，保持不动) ====================

# 2. 绘制图表 (如果处于电脑模式才调用)
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

# 3. 🎯 页面渲染分流机制
if "手机" in view_mode:
    # 📱 手机极简模式：去掉列限制，垂直堆叠，只显示核心数据，屏蔽沉重的图表
    st.markdown("---")
    for name, config in MARKETS.items():
        st.subheader(name)
        tz_obj = pytz.timezone(config["tz"])
        local_time_str = datetime.now(tz_obj).strftime('%m-%d %H:%M')
        st.caption(f"💡 {config['desc']} | 🕒 **{config['tz_name']}: {local_time_str}**")
        
        data = fetch_data(config["ticker"], source=config.get("source", "yahoo"))
        if data is not None and len(data) >= 2:
            current_price = data['Close'].iloc[-1]
            previous_price = data['Close'].iloc[-2]
            change_val = current_price - previous_price
            change_pct = (change_val / previous_price) * 100
            
            # 使用大字体展示核心指标
            st.metric(label="最新价格", value=f"{current_price:.2f}", delta=f"{change_val:.2f} ({change_pct:.2f}%)")
        else:
            st.warning("数据抓取中...")
        st.markdown("---")

else:
    # 💻 电脑模式：保持 3x5 的十五宫格，带有专业图表
    cols = st.columns(3)
    for index, (name, config) in enumerate(MARKETS.items()):
        col = cols[index % 3]
        with col:
            st.subheader(name)
            tz_obj = pytz.timezone(config["tz"])
            local_time_str = datetime.now(tz_obj).strftime('%m-%d %H:%M')
            st.caption(f"💡 {config['desc']} | 🕒 **{config['tz_name']}: {local_time_str}**")
            
            data = fetch_data(config["ticker"], source=config.get("source", "yahoo"))
            if data is not None and len(data) >= 2:
                current_price = data['Close'].iloc[-1]
                previous_price = data['Close'].iloc[-2]
                change_val = current_price - previous_price
                change_pct = (change_val / previous_price) * 100
                last_trade_date = data.index[-1].strftime('%Y-%m-%d')
                
                st.metric(
                    label=f"最新价 (截至: {last_trade_date})", 
                    value=f"{current_price:.2f}", 
                    delta=f"{change_val:.2f} ({change_pct:.2f}%)"
                )
                st.plotly_chart(plot_chart(data, name, config["ma"], view_mode), use_container_width=True)
            else:
                st.warning("数据抓取中或接口受限...")
            st.markdown("---")