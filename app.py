import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import re
import yfinance as yf
import streamlit.components.v1 as components
import plotly.graph_objects as go
import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Callums Terminal",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE SETUP ---
if 'active_view' not in st.session_state:
    st.session_state['active_view'] = "Bitcoin" 
if 'active_chart' not in st.session_state:
    st.session_state['active_chart'] = "COINBASE:BTCUSD"

# --- 3. UI OVERHAUL (CSS INJECTION) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
        
        /* 1. GLOBAL RESET */
        .stApp { 
            background-color: #F3F4F6; /* Cool Grey Background */
            color: #111827; 
            font-family: 'Inter', sans-serif; 
        }
        
        /* 2. REMOVE DEFAULT PADDING */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* 3. SIDEBAR POLISH */
        [data-testid="stSidebar"] { 
            background-color: #FFFFFF; 
            border-right: 1px solid #E5E7EB;
            box-shadow: 4px 0 24px rgba(0,0,0,0.02);
        }
        
        /* 4. CUSTOM HEADER TYPOGRAPHY */
        h1, h2, h3 { 
            font-family: 'Inter', sans-serif;
            color: #111827 !important; 
            font-weight: 700; 
            letter-spacing: -0.5px;
        }
        
        /* 5. PROFESSIONAL BUTTONS (Tickers) */
        div.stButton > button {
            width: 100%;
            background-color: #FFFFFF;
            color: #374151;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 13px;
            font-weight: 600;
            text-align: left;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            border-color: #9CA3AF;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            color: #000;
        }
        div.stButton > button:active {
            background-color: #F3F4F6;
            transform: translateY(0px);
        }

        /* 6. PRIMARY BUTTONS (Generate) */
        button[kind="primary"] {
            background-color: #111827 !important;
            color: #FFFFFF !important;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        button[kind="primary"]:hover {
            background-color: #000000 !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        /* 7. CARDS (The "Glass" Effect) */
        .terminal-card {
            background-color: #FFFFFF; 
            border: 1px solid #E5E7EB; 
            border-radius: 12px;
            padding: 24px; 
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        
        /* 8. STATUS INDICATOR */
        .status-dot {
            height: 8px;
            width: 8px;
            background-color: #10B981;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            box-shadow: 0 0 8px #10B981;
        }
        
        /* 9. METRIC VALUES */
        .metric-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 700;
            color: #111827;
        }
        
        /* 10. TABS OVERHAUL */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            border-bottom: 1px solid #E5E7EB;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            color: #6B7280;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: transparent;
            color: #111827;
            border-bottom: 2px solid #111827;
        }
    </style>
""", unsafe_allow_html=True)

# --- 4. DATA & LOGIC ---

@st.cache_data(ttl=60)
def get_market_data(tickers_dict):
    try:
        data = {}
        for name, symbol in tickers_dict.items():
            if not symbol: continue 
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m")
                if hist.empty: hist = ticker.history(period="2d")
                if not hist.empty:
                    latest = hist['Close'].iloc[-1]
                    open_p = hist['Open'].iloc[0] if len(hist) > 1 else latest
                    change = ((latest - open_p) / open_p) * 100
                    data[name] = (latest, change)
                else: data[name] = (0.0, 0.0)
            except: data[name] = (0.0, 0.0)
        return data
    except: return None

def get_symbol_details(key):
    key_upper = key.upper()
    icon = "📈"
    if "BTC" in key_upper: icon = "₿"
    elif "ETH" in key_upper: icon = "Ξ"
    elif "EUR" in key_upper: icon = "💶"
    elif "GBP" in key_upper: icon = "💷"
    elif "USD" in key_upper: icon = "💵"
    elif "JPY" in key_upper: icon = "¥"
    elif "GOLD" in key_upper: icon = "⚱️"
    elif "OIL" in key_upper: icon = "🛢️"
    elif "NVDA" in key_upper: icon = "🤖"
    elif "AAPL" in key_upper: icon = "🍎"
    return icon

def render_ticker_grid(data):
    if not data: return
    tv_map = {"BTC": "COINBASE:BTCUSD", "ETH": "COINBASE:ETHUSD", "SOL": "COINBASE:SOLUSD", "EUR": "FX:EURUSD", "GBP": "FX:GBPUSD", "JPY": "FX:USDJPY", "CHF": "FX:USDCHF", "CAD": "FX:USDCAD", "AUD": "FX:AUDUSD", "NZD": "FX:NZDUSD", "DXY": "TVC:DXY", "GOLD": "OANDA:XAUUSD", "OIL": "TVC:USOIL", "NVDA": "NASDAQ:NVDA", "TSLA": "NASDAQ:TSLA", "AAPL": "NASDAQ:AAPL", "SPX": "OANDA:SPX500USD", "NDX": "OANDA:NAS100USD"}
    
    # Use 6 columns for a denser, more professional "Toolbar" look
    cols = st.columns(6)
    for i, (key, (price, change)) in enumerate(data.items()):
        icon = get_symbol_details(key)
        arrow = "▲" if change >= 0 else "▼"
        color_code = "#10B981" if change >= 0 else "#EF4444" # Green/Red hex codes
        price_str = f"${price:,.0f}" if price > 100 else f"${price:.4f}"
        
        # We use a button but format the text inside to look like a stat card
        label = f"{icon} {key}   |   {price_str}   {arrow} {change:.2f}%"
        
        with cols[i % 6]:
            if st.button(label, key=f"btn_{key}", use_container_width=True):
                clean_key = key.split("-")[0] if "-" in key else key
                tv_code = tv_map.get(clean_key, tv_map.get(key, "COINBASE:BTCUSD"))
                st.session_state['active_chart'] = tv_code
                st.session_state['active_view'] = "Charts"
                st.rerun()

@st.cache_data(ttl=300)
def get_crypto_fng():
    try: return int(requests.get("https://api.alternative.me/fng/?limit=1").json()['data'][0]['value'])
    except: return 50

@st.cache_data(ttl=300)
def get_macro_fng():
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        score = 100 - ((vix - 10) * 3)
        return max(0, min(100, int(score))), round(vix, 2)
    except: return 50, 0

def render_gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, title={'text': title, 'font': {'size': 14, 'color': '#6B7280'}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#111827"}, 
               'steps': [{'range': [0, 25], 'color': "#FCA5A5"}, {'range': [25, 75], 'color': "#E5E7EB"}, {'range': [75, 100], 'color': "#93C5FD"}]}
    ))
    fig.update_layout(height=180, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'family': "Inter"})
    st.plotly_chart(fig, use_container_width=True)

def render_chart(symbol):
    # Modernized Chart Widget with fewer borders
    html = f"""
    <div class="tradingview-widget-container" style="height:650px;border-radius:12px;overflow:hidden;box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
      <div id="tradingview_{symbol}" style="height:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{"autosize": true, "symbol": "{symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_{symbol}"}});
      </script>
    </div>
    """
    components.html(html, height=650)

def render_economic_calendar(timezone_id):
    calendar_url = f"https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=5,4,72,35,25,6,43,12,37&calType=week&timeZone={timezone_id}&lang=1&importance=3"
    html = f"""
    <div style="border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; height: 800px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <iframe src="{calendar_url}" width="100%" height="800" frameborder="0" allowtransparency="true"></iframe>
    </div>
    """
    components.html(html, height=800)

# --- 5. AI ENGINE (RSS + GOOGLE) ---
@st.cache_data(ttl=600) 
def get_rss_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={query}+when:1d&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.content, features="html.parser")
        items = soup.findAll('item')
        news_text = ""
        for item in items[:15]: 
            title = item.find('title').text if item.find('title') else "No Title"
            pubdate = item.find('pubdate').text if item.find('pubdate') else ""
            news_text += f"- {title} ({pubdate})\n"
        return news_text if news_text else "No recent news found."
    except Exception as e: return f"News Feed Error: {str(e)}"

def resolve_best_model(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'error' in data: return None, data['error']['message']
        valid_models = [m['name'].replace("models/", "") for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        preferred = ["gemini-1.5-flash", "gemini-1.0-pro", "gemini-pro"]
        for p in preferred:
            if p in valid_models: return p, "OK"
        return (valid_models[0], "OK") if valid_models else (None, "No valid models")
    except Exception as e: return None, str(e)

@st.cache_data(ttl=3600, show_spinner="Analyzing...") 
def generate_report(data_dump, mode, api_key):
    if not api_key: return "⚠️ Please enter your Google API Key in the sidebar."
    clean_key = api_key.strip()
    active_model, status = resolve_best_model(clean_key)
    if not active_model: return f"❌ Error: {status}"
    
    headers = {'Content-Type': 'application/json'}
    safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"}]
    generation_config = {"maxOutputTokens": 2500}

    if mode == "BTC":
        prompt = f"""ROLE: Crypto Strategist. TASK: Bitcoin briefing. DATA: {data_dump}. OUTPUT: ### ⚡️ LIVE PULSE\n### 🏦 FLOWS\n### 🔮 SCENARIOS"""
    elif mode == "GEO":
        prompt = f"""ROLE: Risk Analyst. TASK: Global threats. DATA: {data_dump}. OUTPUT: ### 🌍 THREAT MATRIX\n### ⚔️ FLASHPOINTS\n### 🛡 MARKET IMPACT"""
    else: # FX
        prompt = f"""ROLE: FX Strategist. TASK: Detailed Outlook for 7 Major Pairs. DATA: {data_dump}. OUTPUT: **💵 DXY**\n---\n### 🇪🇺 EUR/USD\n### 🇬🇧 GBP/USD\n### 🇯🇵 USD/JPY\n### 🇨🇭 USD/CHF\n### 🇦🇺 AUD/USD\n### 🇨🇦 USD/CAD\n### 🇳🇿 NZD/USD"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={clean_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety_settings, "generationConfig": generation_config}
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].replace("$","USD ") if 'candidates' in r.json() else f"❌ Error: {r.json().get('error', {}).get('message', 'Unknown')}"
    except Exception as e: return f"System Error: {str(e)}"

# --- 6. SIDEBAR (LIVE TERMINAL) ---
with st.sidebar:
    st.markdown("""<div style='margin-bottom: 20px;'><span class='status-dot'></span><span style='font-size: 14px; font-weight: 600; color: #059669;'>SYSTEM ONLINE</span></div>""", unsafe_allow_html=True)
    st.title("💠 Callums Terminal")
    st.caption("v16.0 Obsidian-White")
    
    # Custom Date Display
    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 12px; color: #6B7280; margin-bottom: 20px;'>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>", unsafe_allow_html=True)
    
    api_key = None
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"].strip()
            st.success("🔑 API Key Active")
        else:
            api_key = st.text_input("Enter API Key", type="password")
    except:
        api_key = st.text_input("Enter API Key", type="password")
    
    if api_key: api_key = api_key.strip()
    
    st.markdown("---")
    st.subheader("Settings")
    tz_map = {"London (GMT)": 15, "New York (EST)": 8, "Tokyo (JST)": 18}
    selected_tz = st.selectbox("Timezone:", list(tz_map.keys()), index=0)

# --- 7. MAIN DASHBOARD ---
# Hero Header
st.markdown("## 🖥️ MARKET OVERVIEW")

# Ticker Grid (Hero Section)
col_sel, col_space = st.columns([1, 2])
with col_sel:
    selected_market = st.selectbox("Select Asset Class:", ["Standard", "Crypto", "Forex", "Tech Stocks", "Indices"], index=0, label_visibility="collapsed")

market_map = {
    "Standard": {"BTC": "BTC-USD", "EUR": "EURUSD=X", "USD": "DX-Y.NYB", "GOLD": "GC=F", "OIL": "CL=F", "SPX": "^GSPC"},
    "Crypto": {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD", "DOGE": "DOGE-USD", "ADA": "ADA-USD"},
    "Forex": {"EUR": "EURUSD=X", "GBP": "GBPUSD=X", "JPY": "JPY=X", "CHF": "CHF=X", "CAD": "CAD=X", "AUD": "AUDUSD=X"},
    "Tech Stocks": {"NVDA": "NVDA", "TSLA": "TSLA", "AAPL": "AAPL", "MSFT": "MSFT", "GOOG": "GOOG", "AMZN": "AMZN"},
    "Indices": {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX", "FTSE": "^FTSE", "DAX": "^GDAXI"}
}
active_tickers = market_map[selected_market]
market_data = get_market_data(active_tickers)
render_ticker_grid(market_data)

st.write("") # Spacer

# Navigation
nav_options = ["Bitcoin", "Currencies", "Geopolitics", "Calendar", "Charts"]
cols = st.columns(len(nav_options))
for i, option in enumerate(nav_options):
    if cols[i].button(option, use_container_width=True, type="primary" if st.session_state['active_view'] == option else "secondary"):
        st.session_state['active_view'] = option
        st.rerun()

st.markdown("---")

# View Controller
view = st.session_state['active_view']

if view == "Bitcoin":
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("### Market Sentiment")
        btc_fng = get_crypto_fng()
        st.markdown(f"<div class='terminal-card' style='text-align: center;'><div class='metric-val'>{btc_fng}</div><div style='font-size: 12px; color: #6B7280;'>Fear & Greed Index</div></div>", unsafe_allow_html=True)
        render_gauge(btc_fng, "")
        
    with col_b:
        st.markdown("### 📡 Intelligence Briefing")
        if st.button("GENERATE REPORT", type="primary"):
            raw_news = ""
            with st.spinner("Scanning Institutional Feeds..."):
                raw_news = get_rss_news("Bitcoin crypto market")
            st.info("⚡ Analyzing Market Structure...")
            report = generate_report(raw_news, "BTC", api_key)
            st.session_state['btc_rep'] = report
            st.rerun()
        if 'btc_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["btc_rep"]}</div>', unsafe_allow_html=True)

elif view == "Currencies":
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("### 🌍 Macro Risk")
        macro_score, _ = get_macro_fng()
        st.markdown(f"<div class='terminal-card' style='text-align: center;'><div class='metric-val'>{macro_score}</div><div style='font-size: 12px; color: #6B7280;'>Risk Appetite Score</div></div>", unsafe_allow_html=True)
        render_gauge(macro_score, "")
    with col_b:
        st.markdown("### 💱 FX Strategy Desk")
        if st.button("GENERATE FX OUTLOOK", type="primary"):
            raw_news = ""
            with st.spinner("Aggregating Central Bank Data..."):
                raw_news += get_rss_news("EURUSD GBPUSD USDJPY AUDUSD USDCAD forex")
            st.info("⚡ Synthesizing 7-Pair Analysis...")
            report = generate_report(raw_news, "FX", api_key)
            st.session_state['fx_rep'] = report
            st.rerun()
        if 'fx_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["fx_rep"]}</div>', unsafe_allow_html=True)

elif view == "Geopolitics":
    st.markdown("### 🌐 Global Threat Matrix")
    if st.button("RUN INTEL SCAN", type="primary"):
        raw_news = ""
        with st.spinner("Parsing Classified Wires..."):
            raw_news += get_rss_news("Geopolitics War Oil Gold Economy")
        st.info("⚡ Assessing Strategic Risks...")
        report = generate_report(raw_news, "GEO", api_key)
        st.session_state['geo_rep'] = report
        st.rerun()
    if 'geo_rep' in st.session_state:
        st.markdown(f'<div class="terminal-card">{st.session_state["geo_rep"]}</div>', unsafe_allow_html=True)

elif view == "Calendar":
    st.markdown("### 📅 Economic Calendar")
    render_economic_calendar(tz_map[selected_tz])

elif view == "Charts":
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"{st.session_state['active_chart']}")
    with col2:
        asset_map = {
            "Bitcoin (BTC/USD)": "COINBASE:BTCUSD", "Ethereum (ETH/USD)": "COINBASE:ETHUSD",
            "Ripple (XRP/USD)": "COINBASE:XRPUSD", "Gold (XAU/USD)": "OANDA:XAUUSD",
            "Crude Oil (WTI)": "TVC:USOIL", "Dollar Index (DXY)": "TVC:DXY",
            "EUR / USD": "FX:EURUSD", "GBP / USD": "FX:GBPUSD", "USD / JPY": "FX:USDJPY",
            "USD / CHF": "FX:USDCHF", "AUD / USD": "FX:AUDUSD", "USD / CAD": "FX:USDCAD",
            "NZD / USD": "FX:NZDUSD"
        }
        default_ix = 0
        current_val = st.session_state['active_chart']
        vals = list(asset_map.values())
        if current_val in vals: default_ix = vals.index(current_val)
        selected_label = st.selectbox("Quick Switch:", list(asset_map.keys()), index=default_ix, label_visibility="collapsed")
        
        if asset_map[selected_label] != current_val:
            st.session_state['active_chart'] = asset_map[selected_label]
            st.rerun()
            
    render_chart(st.session_state['active_chart'])
