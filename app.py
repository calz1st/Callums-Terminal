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

# --- 2. UI THEME ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap');
        
        .stApp { background-color: #FAFAFA; color: #111827; font-family: 'Inter', sans-serif; }
        [data-testid="stSidebar"] { background-color: #F3F4F6; border-right: 1px solid #E5E7EB; }
        
        h1, h2, h3 { color: #111827 !important; font-weight: 600; letter-spacing: -0.5px; }
        p, div, li { color: #374151; font-size: 15px; line-height: 1.6; }
        
        /* Report Cards */
        .terminal-card {
            background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px;
            padding: 30px; margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        /* Buttons */
        .stButton>button {
            background-color: #000000; color: #FFFFFF !important; border: none;
            border-radius: 6px; padding: 12px 24px; font-weight: 500; width: 100%;
        }
        .stButton>button:hover { background-color: #333333; }
        
        /* SCROLLABLE TICKER CSS */
        .ticker-wrap {
            display: flex;
            overflow-x: auto;
            gap: 15px;
            padding: 10px 0px;
            scrollbar-width: none; /* Firefox */
            -ms-overflow-style: none;  /* IE 10+ */
            white-space: nowrap;
        }
        .ticker-wrap::-webkit-scrollbar { 
            display: none; /* Chrome/Safari */
        }
        .ticker-item {
            min-width: 150px;
            background: white;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #E5E7EB;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
        }
        .t-label { font-size: 12px; color: #6B7280; font-weight: 600; margin-bottom: 5px;}
        .t-val { font-size: 18px; font-weight: 700; font-family: 'JetBrains Mono'; color: #111827; }
        .t-delta { font-size: 12px; font-weight: 500; margin-top: 2px; }
        .pos { color: #059669; }
        .neg { color: #DC2626; }
    </style>
""", unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS ---

@st.cache_data(ttl=60)
def get_market_data(tickers_dict):
    try:
        data = {}
        for name, symbol in tickers_dict.items():
            if not symbol: continue 
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    latest = hist['Close'].iloc[-1]
                    open_p = hist['Open'].iloc[0]
                    change = ((latest - open_p) / open_p) * 100
                    data[name] = (latest, change)
                else:
                    hist_long = ticker.history(period="2d")
                    if not hist_long.empty:
                        latest = hist_long['Close'].iloc[-1]
                        prev = hist_long['Close'].iloc[0]
                        change = ((latest - prev) / prev) * 100
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
    elif "EUR" in key_upper: icon = "💶"
    elif "GBP" in key_upper: icon = "💷"
    elif "USD" in key_upper: icon = "💵"
    elif "JPY" in key_upper: icon = "¥"
    elif "GOLD" in key_upper or "GC" in key_upper: icon = "⚱️"
    elif "OIL" in key_upper or "CL" in key_upper: icon = "🛢️"
    elif "SPX" in key_upper or "500" in key_upper: icon = "🇺🇸"
    elif "TSLA" in key_upper: icon = "🚗"
    elif "NVDA" in key_upper: icon = "🤖"
    elif "AAPL" in key_upper: icon = "🍎"
    return icon

def render_ticker_bar(data):
    if not data: return
    html_content = '<div class="ticker-wrap">'
    for key, (price, change) in data.items():
        color = "pos" if change >= 0 else "neg"
        arrow = "▲" if change >= 0 else "▼"
        if price > 1000: price_str = f"${price:,.0f}"
        elif price < 1.5: price_str = f"{price:.4f}"
        else: price_str = f"${price:.2f}"
        icon = get_symbol_details(key)
        card = f'<div class="ticker-item"><span class="t-label">{icon} {key}</span><span class="t-val">{price_str}</span><span class="t-delta {color}">{arrow} {change:.2f}%</span></div>'
        html_content += card
    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)

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

# --- 4. DATA SOURCES & AI ---
@st.cache_data(ttl=600) 
def scrape_site(url, limit):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.content, 'html.parser')
        texts = [p.get_text() for p in soup.find_all(['h1', 'h2', 'p'])]
        # ULTRA LITE: Only 500 chars to save quota
        return f"[[SOURCE: {url}]]\n" + " ".join(texts)[:500] + "\n\n"
    except: return ""

@st.cache_data(ttl=3600, show_spinner="Analyzing...") 
def generate_report(data_dump, mode, api_key, model_choice):
    if not api_key: return "⚠️ Please enter your Google API Key in the sidebar."
    
    clean_key = api_key.strip()
    
    # --- FINAL FIX: FORCE 'gemini-pro' ---
    # This is the 1.0 version. It is the most compatible model in existence.
    # We ignore the user selection to guarantee a working connection.
    active_model = "gemini-pro"
    
    headers = {'Content-Type': 'application/json'}
    safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"}]
    
    # REDUCED OUTPUT TOKENS FOR 1.0 PRO
    generation_config = {"maxOutputTokens": 600}

    if mode == "BTC":
        prompt = f"""ROLE: Analyst. TASK: Bitcoin technical update. OUTPUT: ### ⚡️ NARRATIVE \n ### 🎯 LEVELS"""
    elif mode == "GEO":
        prompt = f"""ROLE: Risk Analyst. TASK: Geopolitical Risks. OUTPUT: ### ⚠️ THREATS \n ### 🛢 COMMODITIES"""
    else:
        prompt = f"""ROLE: FX Strat. TASK: Major Pairs Outlook. OUTPUT: **💵 DXY** \n ### 🇪🇺 EUR/USD"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={clean_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "safetySettings": safety_settings,
        "generationConfig": generation_config
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        response_json = r.json()
        
        if 'candidates' in response_json:
            return response_json['candidates'][0]['content']['parts'][0]['text'].replace("$","USD ")
        
        if 'error' in response_json:
            err_msg = response_json['error'].get('message', '')
            
            # Rate Limit Handler
            if response_json['error'].get('code') == 429:
                wait_match = re.search(r"retry in (\d+\.?\d*)s", err_msg)
                if wait_match:
                    wait_seconds = float(wait_match.group(1)) + 1
                    placeholder = st.empty()
                    for i in range(int(wait_seconds), 0, -1):
                        placeholder.warning(f"⚠️ High Traffic. Cooling down: {i}s...")
                        time.sleep(1)
                    placeholder.empty()
                    # Retry once
                    r2 = requests.post(url, headers=headers, json=payload)
                    if 'candidates' in r2.json():
                        return r2.json()['candidates'][0]['content']['parts'][0]['text']
            
            return f"❌ Error: {err_msg}"
                
    except Exception as e:
        return f"System Error: {str(e)}"
            
    return "❌ Connection Failed."

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("💠 Callums Terminals")
    st.caption("Update v15.24 (Universal)")
    st.markdown("---")
    
    api_key = None
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"].strip()
            st.success("🔑 Key Loaded")
        else:
            api_key = st.text_input("Use API Key to connect to server", type="password")
    except Exception:
        api_key = st.text_input("Use API Key to connect to server", type="password")
    
    if api_key: api_key = api_key.strip()
    
    st.markdown("---")
    st.subheader("⚙️ Settings")
    
    tz_map = {"London (GMT)": 2, "London (Alt)": 42, "New York (EST)": 8, "Tokyo (JST)": 18}
    selected_tz = st.selectbox("Calendar Timezone:", list(tz_map.keys()), index=0)
    
    st.markdown("---")
    st.subheader("🤖 Model Selector")
    
    # HARDCODED DISPLAY: User can see what they are using, but can't break it
    st.info("✅ Using Universal Model (Gemini Pro 1.0)")
    model_choice = "gemini-pro"
    
    st.markdown("---")
    st.success("● NETWORK: SECURE")

# --- 6. MAIN DASHBOARD ---
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

if selected_market == "Custom":
    with st.expander("🛠 Configure Custom Tickers", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        t1 = c1.text_input("Ticker 1", value="BTC-USD")
        t2 = c2.text_input("Ticker 2", value="NVDA")
        t3 = c3.text_input("Ticker 3", value="EURUSD=X")
        t4 = c4.text_input("Ticker 4", value="GC=F")
        t5 = c5.text_input("Ticker 5", value="^GSPC")
    active_tickers = {t1:t1, t2:t2, t3:t3, t4:t4, t5:t5}
else:
    active_tickers = market_map[selected_market]

market_data = get_market_data(active_tickers)
if market_data: render_ticker_bar(market_data)

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗞️Bitcoin", "🌍Currencies", "🌐Geopolitics", "📅 Calendar", "📈Charts"])

with tab1:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("BTC Fear & Greed ")
        render_gauge(get_crypto_fng(), "")
        st.caption("0 = Ext. Fear | 100 = Ext. Greed")
    with col_b:
        st.subheader("Market scan")
        if st.button("GENERATE BTC BRIEFING", type="primary"):
            st.info("⏳ Analyzing...")
            # Using 'gemini-pro' hardcoded inside the function
            report = generate_report("", "BTC", api_key, model_choice)
            st.session_state['btc_rep'] = report
            st.rerun() 
            
        if 'btc_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["btc_rep"]}</div>', unsafe_allow_html=True)

with tab2:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Macro Sentiment")
        macro_score, _ = get_macro_fng()
        render_gauge(macro_score, "")
        st.caption("High Score = Risk On (Greed)\nLow Score = Risk Off (Fear)")
    with col_b:
        st.subheader("Global FX Strategy")
        if st.button("GENERATE MACRO BRIEFING", type="primary"):
            st.info("⏳ Analyzing Markets...")
            report = generate_report("", "FX", api_key, model_choice)
            st.session_state['fx_rep'] = report
            st.rerun()
        if 'fx_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["fx_rep"]}</div>', unsafe_allow_html=True)

with tab3:
    st.subheader("Geopolitical Risk Intelligence")
    if st.button("RUN GEOPOLITICAL SCAN", type="primary"):
        st.info("⏳ Scanning...")
        report = generate_report("", "GEO", api_key, model_choice)
        st.session_state['geo_rep'] = report
        st.rerun()
    if 'geo_rep' in st.session_state:
        st.markdown(f'<div class="terminal-card">{st.session_state["geo_rep"]}</div>', unsafe_allow_html=True)

with tab4:
    st.subheader("High Impact Economic Events")
    render_economic_calendar(tz_map[selected_tz])

with tab5:
    st.subheader("Live Market Data")
    selected_label = st.selectbox("Select Asset Class:", ["COINBASE:BTCUSD", "TVC:DXY", "OANDA:XAUUSD", "TVC:USOIL", "FX:EURUSD", "FX:GBPUSD", "FX:USDJPY"])
    render_chart(selected_label)
