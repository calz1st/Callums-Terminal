import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import re
import yfinance as yf
import streamlit.components.v1 as components
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="QUANTUM | Hedge Fund Terminal",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE SETUP ---
if 'active_view' not in st.session_state:
    st.session_state['active_view'] = "Bitcoin" 
if 'active_chart' not in st.session_state:
    st.session_state['active_chart'] = "COINBASE:BTCUSD"

# --- 3. UI THEME ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap');
        
        .stApp { background-color: #FAFAFA; color: #111827; font-family: 'Inter', sans-serif; }
        [data-testid="stSidebar"] { background-color: #F3F4F6; border-right: 1px solid #E5E7EB; }
        
        h1, h2, h3 { color: #111827 !important; font-weight: 600; letter-spacing: -0.5px; }
        p, div, li { color: #374151; font-size: 15px; line-height: 1.6; }
        
        /* Button Styling to look like Tickers */
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            border: 1px solid #E5E7EB;
            background-color: white;
            color: #111827;
            text-align: left;
            padding: 10px 15px;
            transition: all 0.2s;
        }
        div.stButton > button:hover {
            border-color: #000;
            background-color: #F9FAFB;
            transform: translateY(-2px);
        }
        /* Active State Highlight */
        div.stButton > button:focus {
            border-color: #000;
            background-color: #F3F4F6;
        }
        
        .terminal-card {
            background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px;
            padding: 30px; margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# --- 4. HELPER FUNCTIONS ---

@st.cache_data(ttl=60)
def get_market_data(tickers_dict):
    try:
        data = {}
        for name, symbol in tickers_dict.items():
            if not symbol: continue 
            try:
                ticker = yf.Ticker(symbol)
                # Fast Fetch
                hist = ticker.history(period="1d", interval="1m")
                if hist.empty: hist = ticker.history(period="2d")
                
                if not hist.empty:
                    latest = hist['Close'].iloc[-1]
                    open_p = hist['Open'].iloc[0] if len(hist) > 1 else latest
                    change = ((latest - open_p) / open_p) * 100
                    data[name] = (latest, change)
                else:
                    data[name] = (0.0, 0.0)
            except:
                data[name] = (0.0, 0.0)
        return data
    except: return None

def get_symbol_details(key):
    key_upper = key.upper()
    icon = "📈"
    if "BTC" in key_upper: icon = "₿"
    elif "ETH" in key_upper: icon = "Ξ"
    elif "XRP" in key_upper: icon = "✕"
    elif "EUR" in key_upper: icon = "💶"
    elif "GBP" in key_upper: icon = "💷"
    elif "USD" in key_upper: icon = "💵"
    elif "JPY" in key_upper: icon = "¥"
    elif "GOLD" in key_upper: icon = "⚱️"
    elif "OIL" in key_upper: icon = "🛢️"
    elif "NVDA" in key_upper: icon = "🤖"
    elif "AAPL" in key_upper: icon = "🍎"
    return icon

def render_ticker_grid(data, asset_map):
    """
    Replaces HTML ticker tape with a NATIVE STREAMLIT GRID.
    This guarantees buttons are clickable.
    """
    if not data: return

    # Define TradingView Mapping for Click Action
    tv_map = {
        "BTC": "COINBASE:BTCUSD", "ETH": "COINBASE:ETHUSD", "SOL": "COINBASE:SOLUSD", "XRP": "COINBASE:XRPUSD",
        "EUR": "FX:EURUSD", "GBP": "FX:GBPUSD", "JPY": "FX:USDJPY", "CHF": "FX:USDCHF",
        "CAD": "FX:USDCAD", "AUD": "FX:AUDUSD", "NZD": "FX:NZDUSD",
        "DXY": "TVC:DXY", "GOLD": "OANDA:XAUUSD", "OIL": "TVC:USOIL",
        "NVDA": "NASDAQ:NVDA", "TSLA": "NASDAQ:TSLA", "AAPL": "NASDAQ:AAPL",
        "SPX": "OANDA:SPX500USD", "NDX": "OANDA:NAS100USD"
    }

    # Create 5 columns for the grid
    cols = st.columns(5)
    
    for i, (key, (price, change)) in enumerate(data.items()):
        # Format the text
        icon = get_symbol_details(key)
        arrow = "▲" if change >= 0 else "▼"
        price_str = f"${price:,.0f}" if price > 100 else f"${price:.4f}"
        
        # Determine label text
        label = f"{icon} {key}\n{price_str} ({arrow} {change:.2f}%)"
        
        # Place button in column (modulo 5)
        with cols[i % 5]:
            # THE MAGIC: A real Streamlit button
            if st.button(label, key=f"btn_{key}", use_container_width=True):
                # Action: Update Chart & Switch Tab
                clean_key = key.split("-")[0] if "-" in key else key
                # Find TV code
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
    colors = ["#EF4444", "#FCA5A5", "#E5E7EB", "#93C5FD", "#3B82F6"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, title={'text': title},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#111827"}, 
               'steps': [{'range': [0, 25], 'color': colors[0]}, {'range': [25, 45], 'color': colors[1]},
                         {'range': [45, 55], 'color': colors[2]}, {'range': [55, 75], 'color': colors[3]},
                         {'range': [75, 100], 'color': colors[4]}]}
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

def render_chart(symbol):
    html = f"""
    <div class="tradingview-widget-container" style="height:600px;border-radius:8px;overflow:hidden;border:1px solid #E5E7EB;">
      <div id="tradingview_{symbol}" style="height:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{"autosize": true, "symbol": "{symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_{symbol}"}});
      </script>
    </div>
    """
    components.html(html, height=600)

def render_economic_calendar(timezone_id):
    calendar_url = f"https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=5,4,72,35,25,6,43,12,37&calType=week&timeZone={timezone_id}&lang=1&importance=3"
    html = f"""
    <div style="border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; height: 800px;">
        <iframe src="{calendar_url}" width="100%" height="800" frameborder="0" allowtransparency="true"></iframe>
    </div>
    """
    components.html(html, height=800)

# --- 5. DATA SOURCES & AI ---

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
    # LIMIT: 2500 Tokens (Optimized)
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

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("💠 Callums Terminals")
    st.caption("Update v15.38 (Expanded Charts)")
    st.markdown("---")
    
    api_key = None
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"].strip()
            st.success("🔑 Key Loaded")
        else:
            api_key = st.text_input("Use API Key", type="password")
    except:
        api_key = st.text_input("Use API Key", type="password")
    
    if api_key: api_key = api_key.strip()
    
    st.markdown("---")
    st.subheader("⚙️ Settings")
    tz_map = {"London (GMT)": 2, "New York (EST)": 8, "Tokyo (JST)": 18}
    selected_tz = st.selectbox("Timezone:", list(tz_map.keys()), index=0)
    
    st.markdown("---")
    if api_key: st.success("● NETWORK: SECURE")

# --- 7. MAIN DASHBOARD ---
st.title("TERMINAL DASHBOARD 🖥️")
st.markdown("---")

col_sel, col_space = st.columns([1, 2])
with col_sel:
    selected_market = st.selectbox("Select Market View:", ["Standard", "Crypto", "Forex", "Tech Stocks", "Indices", "Custom"], index=0)

market_map = {
    "Standard": {"BTC": "BTC-USD", "EUR": "EURUSD=X", "USD": "DX-Y.NYB", "GOLD": "GC=F", "OIL": "CL=F"},
    "Crypto": {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD", "DOGE": "DOGE-USD"},
    "Forex": {"EUR": "EURUSD=X", "GBP": "GBPUSD=X", "JPY": "JPY=X", "CHF": "CHF=X", "CAD": "CAD=X"},
    "Tech Stocks": {"NVDA": "NVDA", "TSLA": "TSLA", "AAPL": "AAPL", "MSFT": "MSFT", "GOOG": "GOOG"},
    "Indices": {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX", "FTSE": "^FTSE"}
}
active_tickers = market_map[selected_market]
market_data = get_market_data(active_tickers)

# --- REPLACED HTML BAR WITH NATIVE GRID ---
if market_data:
    render_ticker_grid(market_data, market_map)

st.markdown("---")

# --- NAVIGATION MENU ---
nav_options = ["Bitcoin", "Currencies", "Geopolitics", "Calendar", "Charts"]
cols = st.columns(len(nav_options))
for i, option in enumerate(nav_options):
    if cols[i].button(option, use_container_width=True, type="primary" if st.session_state['active_view'] == option else "secondary"):
        st.session_state['active_view'] = option
        st.rerun()

st.markdown("---")

# --- VIEW CONTROLLER ---
view = st.session_state['active_view']

if view == "Bitcoin":
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("BTC Fear & Greed")
        render_gauge(get_crypto_fng(), "")
    with col_b:
        st.subheader("Market scan")
        if st.button("GENERATE BTC BRIEFING", type="primary"):
            raw_news = ""
            with st.spinner("Streaming Google News Feed..."):
                raw_news = get_rss_news("Bitcoin crypto")
            st.info("⏳ Analyzing Live Headlines...")
            report = generate_report(raw_news, "BTC", api_key)
            st.session_state['btc_rep'] = report
            st.rerun()
        if 'btc_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["btc_rep"]}</div>', unsafe_allow_html=True)

elif view == "Currencies":
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Macro Sentiment")
        macro_score, _ = get_macro_fng()
        render_gauge(macro_score, "")
    with col_b:
        st.subheader("Global FX Strategy")
        if st.button("GENERATE MACRO BRIEFING", type="primary"):
            raw_news = ""
            with st.spinner("Streaming Google News Feed..."):
                raw_news += get_rss_news("EURUSD GBPUSD USDJPY AUDUSD USDCAD forex")
            st.info("⏳ Analyzing Live Headlines...")
            report = generate_report(raw_news, "FX", api_key)
            st.session_state['fx_rep'] = report
            st.rerun()
        if 'fx_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["fx_rep"]}</div>', unsafe_allow_html=True)

elif view == "Geopolitics":
    st.subheader("Geopolitical Risk Intelligence")
    if st.button("RUN GEOPOLITICAL SCAN", type="primary"):
        raw_news = ""
        with st.spinner("Streaming Google News Feed..."):
            raw_news += get_rss_news("Geopolitics War Oil Gold Economy")
        st.info("⏳ Analyzing Live Headlines...")
        report = generate_report(raw_news, "GEO", api_key)
        st.session_state['geo_rep'] = report
        st.rerun()
    if 'geo_rep' in st.session_state:
        st.markdown(f'<div class="terminal-card">{st.session_state["geo_rep"]}</div>', unsafe_allow_html=True)

elif view == "Calendar":
    st.subheader("High Impact Economic Events")
    render_economic_calendar(tz_map[selected_tz])

elif view == "Charts":
    st.subheader(f"Live Chart: {st.session_state['active_chart']}")
    
    # --- UPDATED ASSET MAP FOR CHARTS TAB ---
    asset_map = {
        "Bitcoin (BTC/USD)": "COINBASE:BTCUSD",
        "Ethereum (ETH/USD)": "COINBASE:ETHUSD",
        "Ripple (XRP/USD)": "COINBASE:XRPUSD",
        "Gold (XAU/USD)": "OANDA:XAUUSD",
        "Crude Oil (WTI)": "TVC:USOIL",
        "Dollar Index (DXY)": "TVC:DXY",
        "EUR / USD": "FX:EURUSD",
        "GBP / USD": "FX:GBPUSD",
        "USD / JPY": "FX:USDJPY",
        "USD / CHF": "FX:USDCHF",
        "AUD / USD": "FX:AUDUSD",
        "USD / CAD": "FX:USDCAD",
        "NZD / USD": "FX:NZDUSD",
    }
    
    # Auto-select the active chart in dropdown
    default_ix = 0
    current_val = st.session_state['active_chart']
    vals = list(asset_map.values())
    if current_val in vals:
        default_ix = vals.index(current_val)
        
    selected_label = st.selectbox("Select Asset Class:", list(asset_map.keys()), index=default_ix)
    
    if asset_map[selected_label] != current_val:
        st.session_state['active_chart'] = asset_map[selected_label]
        st.rerun()
        
    render_chart(st.session_state['active_chart'])
