import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
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

def get_market_data(category):
    """Fetches real-time prices based on selected category."""
    try:
        data = {}
        
        # DEFINING THE MARKET BASKETS
        market_map = {
            "Standard": {
                "BTC": "BTC-USD", "EUR": "EURUSD=X", "USD": "DX-Y.NYB", "GOLD": "GC=F", "OIL": "CL=F"
            },
            "Crypto": {
                "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD", "DOGE": "DOGE-USD"
            },
            "Forex": {
                "EUR": "EURUSD=X", "GBP": "GBPUSD=X", "JPY": "JPY=X", "CHF": "CHF=X", "CAD": "CAD=X"
            },
            "Tech Stocks": {
                "NVDA": "NVDA", "TSLA": "TSLA", "AAPL": "AAPL", "MSFT": "MSFT", "GOOG": "GOOG"
            },
            "Indices": {
                "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX", "FTSE": "^FTSE"
            }
        }
        
        tickers = market_map.get(category, market_map["Standard"])
        
        for name, symbol in tickers.items():
            ticker = yf.Ticker(symbol)
            # Fast fetch for 1 day history
            hist = ticker.history(period="1d", interval="1m")
            
            if not hist.empty:
                latest = hist['Close'].iloc[-1]
                open_p = hist['Open'].iloc[0]
                change = ((latest - open_p) / open_p) * 100
                data[name] = (latest, change)
            else:
                data[name] = (0.0, 0.0)
        return data
    except: return None

def render_ticker_bar(data):
    """Generates the horizontal scrollable HTML bar."""
    if not data: return
    
    html_content = '<div class="ticker-wrap">'
    
    # Generic icon mapping fallback
    icon_map = {
        "BTC": "₿", "ETH": "Ξ", "SOL": "◎", "EUR": "💶", "GBP": "💷", 
        "USD": "💵", "GOLD": "⚱️", "OIL": "🛢️", "NVDA": "🤖", "TSLA": "🚗",
        "S&P 500": "🇺🇸", "VIX": "📉"
    }
    
    for key, (price, change) in data.items():
        color = "pos" if change >= 0 else "neg"
        arrow = "▲" if change >= 0 else "▼"
        
        # Smart formatting based on asset price (e.g. BTC vs Forex)
        if price > 1000:
            price_str = f"${price:,.0f}"
        elif price < 2: 
            price_str = f"{price:.4f}"
        else:
            price_str = f"${price:.2f}"
            
        icon = icon_map.get(key, "📈")
        
        card = f'<div class="ticker-item"><span class="t-label">{icon} {key}</span><span class="t-val">{price_str}</span><span class="t-delta {color}">{arrow} {change:.2f}%</span></div>'
        html_content += card
            
    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)

def get_crypto_fng():
    try: return int(requests.get("https://api.alternative.me/fng/?limit=1").json()['data'][0]['value'])
    except: return 50

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

def render_economic_calendar():
    """Embeds Investing.com Calendar Filtered for High Impact (Red) News Only."""
    calendar_url = "https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=5,4,72,35,25,6,43,12,37&calType=week&timeZone=8&lang=1&importance=3"
    html = f"""
    <div style="border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; height: 800px;">
        <iframe src="{calendar_url}" 
        width="100%" height="800" frameborder="0" allowtransparency="true"></iframe>
    </div>
    """
    components.html(html, height=800)

# --- 4. DATA SOURCES & AI ---
BTC_SOURCES = ["https://cointelegraph.com/tags/bitcoin", "https://u.today/bitcoin-news"]
FX_SOURCES = ["https://www.fxstreet.com/news", "https://www.dailyfx.com/market-news"]
GEO_SOURCES = ["https://oilprice.com/Geopolitics", "https://www.fxstreet.com/news/macroeconomics", "https://www.cnbc.com/world/?region=world"]

def scrape_site(url, limit):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.content, 'html.parser')
        texts = [p.get_text() for p in soup.find_all(['h1', 'h2', 'p'])]
        return f"[[SOURCE: {url}]]\n" + " ".join(texts)[:limit] + "\n\n"
    except: return ""

def list_available_models(api_key):
    """
    Diagnostic Tool: Lists all models available to your key.
    We filter for models that support 'generateContent'.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'error' in data:
            return []
            
        # Extract CLEAN names (remove 'models/' prefix)
        valid_models = [
            m['name'].replace("models/", "") 
            for m in data.get('models', []) 
            if 'generateContent' in m['supportedGenerationMethods']
        ]
        return valid_models
    except:
        return []

def generate_report(data_dump, mode, api_key, model_choice):
    if not api_key: return "⚠️ Please enter your Google API Key in the sidebar."
    
    # --- WATERFALL STRATEGY ---
    fallback_chain = [model_choice]
    safe_defaults = ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash"]
    for m in safe_defaults:
        if m not in fallback_chain: fallback_chain.append(m)

    headers = {'Content-Type': 'application/json'}
    safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"}]

    if mode == "BTC":
        prompt_text = f"""
        ROLE: Senior Hedge Fund Analyst.
        TASK: Write a comprehensive Bitcoin briefing.
        DATA: {data_dump[:15000]}
        OUTPUT FORMAT (Markdown):
        ### ⚡️ BITCOIN EXECUTIVE SUMMARY
        (Current Price Action & Narrative)
        ### 🐋 ORDER FLOW & SENTIMENT
        (ETF Flows, Whale Activity, Fear/Greed)
        ### 🧱 KEY LEVELS
        (Support/Resistance & Liquidity)
        ### 🎯 TRADE PLAN
        (Bull/Bear Scenarios)
        """
        
    elif mode == "GEO":
        prompt_text = f"""
        ROLE: Geopolitical Risk Strategist.
        TASK: Analyze events through MARKET IMPACT.
        DATA: {data_dump[:15000]}
        
        OUTPUT FORMAT (Strict Markdown - Insert \\n\\n before every header):
        
        ### ⚠️ GEOPOLITICAL THREAT ASSESSMENT
        **Current Status:** (Low / Elevated / Critical)
        **Market Focus:** (e.g., "Middle East Tensions")
        
        ---
        ### 🛢 ENERGY & COMMODITIES
        (Impact on supply chains/Gold demand)
        
        ---
        ### 🛡 DEFENSE & SECURITY
        (Conflict zone developments)
        
        ---
        ### 💵 FX & SOVEREIGN RISK
        (USD Safe Haven vs EM Risk)
        """

    else: # FX Mode
        prompt_text = f"""
        ROLE: Global Macro Strategist (Forex Desk).
        TASK: Detailed breakdown for the 7 Major Currencies based on the provided data.
        DATA: {data_dump[:15000]}
        
        OUTPUT FORMAT (Strict Markdown - IMPORTANT: You MUST put TWO NEWLINES (\\n\\n) before every header):

        **💵 US DOLLAR INDEX (DXY) & MACRO**
        (Advanced, concise synthesis of DXY structure, Yield Curve dynamics, and Global Liquidity conditions.)

        ---
        
        ### 🇪🇺 EUR/USD
        * **Overview:** (Context & Price Action)
        * **Bias:** (Bullish / Bearish / Neutral)
        * **News Impacts:** (ECB policy, Data releases)
        * **Sentiment:** (Institutional positioning)

        ---
        
        ### 🇬🇧 GBP/USD
        * **Overview:** (Context & Price Action)
        * **Bias:** (Bullish / Bearish / Neutral)
        * **News Impacts:** (BoE policy, UK Data)
        * **Sentiment:** (Institutional positioning)

        ---
        
        ### 🇯🇵 USD/JPY
        * **Overview:** (Context & Price Action)
        * **Bias:** (Bullish / Bearish / Neutral)
        * **News Impacts:** (BoJ interventions, Yield spreads)
        * **Sentiment:** (Carry trade flows)

        ---
        
        ### 🇨🇭 USD/CHF
        * **Overview:** (Safe haven status & SNB)
        * **Bias:** (Direction)
        
        ---
        
        ### 🇦🇺 AUD/USD
        * **Overview:** (Commodities & China correlation)
        * **Bias:** (Direction)

        ---
        
        ### 🇨🇦 USD/CAD
        * **Overview:** (Oil correlation & BoC)
        * **Bias:** (Direction)

        ---
        
        ### 🇳🇿 NZD/USD
        * **Overview:** (Agri-commodities & RBNZ)
        * **Bias:** (Direction)
        """

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "safetySettings": safety_settings
    }
    
    # 4. ROBUST RETRY LOOP
    for model in fallback_chain:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        wait_times = [4, 8]
        for wait in wait_times:
            try:
                r = requests.post(url, headers=headers, json=payload)
                response_json = r.json()
                if 'candidates' in response_json and len(response_json['candidates']) > 0:
                    return response_json['candidates'][0]['content']['parts'][0]['text'].replace("$","USD ")
                if 'error' in response_json:
                    code = response_json['error'].get('code', 0)
                    if code == 429 or code == 503:
                        time.sleep(wait)
                        continue
                    if code == 404: break 
            except Exception:
                time.sleep(1); continue
                
    return "⚠️ System Overloaded: All AI models are busy. Please wait 60 seconds."

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("💠 Callums Terminal")
    st.caption("Update v15.6")
    st.markdown("---")
    api_key = st.text_input("Use API Key to connect to server", type="password")
    
    st.markdown("---")
    st.subheader("⚙️ Model Selector")
    st.info("⚠️ Note: Terminal will auto-connect to most capable server")
    
    available_models = []
    if api_key:
        if 'valid_models' not in st.session_state:
            with st.spinner("Scanning Account Models..."):
                found = list_available_models(api_key)
                if found:
                    st.session_state['valid_models'] = found
                    st.success(f"Verified: {len(found)} Models Found")
        
        available_models = st.session_state.get('valid_models', [])

    if available_models:
        model_options = available_models
        default_index = 0
        for i, m in enumerate(model_options):
            if "gemini-2.0-flash" in m and "exp" not in m:
                default_index = i
                break
            elif "gemini-2.0-flash-exp" in m:
                default_index = i
    else:
        model_options = ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-2.5-flash"]
        default_index = 0

    model_choice = st.selectbox("Active Model:", model_options, index=default_index)
    
    st.markdown("---")
    st.success("● NETWORK: SECURE")

# --- 6. MAIN DASHBOARD ---
st.title("TERMINAL DASHBOARD 🖥️")
st.markdown("---")

# MARKET SELECTOR DROPDOWN (Dynamic Tickers)
selected_market = st.selectbox(
    "Select Market View:", 
    ["Standard", "Crypto", "Forex", "Tech Stocks", "Indices"],
    index=0
)

# LIVE TICKERS (FIXED LAYOUT)
market = get_market_data(selected_market)
if market:
    render_ticker_bar(market)

st.markdown("---")

# TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗞️Bitcoin", "🌍Currencies", "🌐Geopolitics", "📅 Calendar", "📈Charts"])

with tab1:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("BTC Fear & Greed ")
        btc_fng = get_crypto_fng()
        render_gauge(btc_fng, "")
        st.caption("0 = Ext. Fear | 100 = Ext. Greed")
        
    with col_b:
        st.subheader("Market scan")
        if st.button("GENERATE BTC BRIEFING", type="primary"):
            with st.status("Accessing Institutional Feeds...", expanded=True):
                raw = ""
                for s in BTC_SOURCES: raw += scrape_site(s, 5000)
                st.write("Synthesizing Report...")
                report = generate_report(raw, "BTC", api_key, model_choice)
                st.session_state['btc_rep'] = report
        
        if 'btc_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["btc_rep"]}</div>', unsafe_allow_html=True)

with tab2:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Macro Sentiment")
        macro_score, vix_val = get_macro_fng()
        render_gauge(macro_score, f"")
        st.caption("High Score = Risk On (Greed)\nLow Score = Risk Off (Fear)")
        
    with col_b:
        st.subheader("Global FX Strategy")
        if st.button("GENERATE MACRO BRIEFING", type="primary"):
            with st.status("Analyzing 7 Majors...", expanded=True):
                raw = ""
                for s in FX_SOURCES: raw += scrape_site(s, 5000)
                st.write("Running Quant Analysis...")
                report = generate_report(raw, "FX", api_key, model_choice)
                st.session_state['fx_rep'] = report
        
        if 'fx_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["fx_rep"]}</div>', unsafe_allow_html=True)

with tab3:
    st.subheader("Geopolitical Risk Intelligence")
    st.caption("Monitoring Conflict Zones, Trade Wars & Energy Security through a Market Lens.")
    
    if st.button("RUN GEOPOLITICAL SCAN", type="primary"):
        with st.status("Scanning Classified Channels...", expanded=True):
            raw = ""
            for s in GEO_SOURCES: raw += scrape_site(s, 5000)
            st.write("Assessing Threat/volatility Levels...")
            report = generate_report(raw, "GEO", api_key, model_choice)
            st.session_state['geo_rep'] = report

    if 'geo_rep' in st.session_state:
        st.markdown(f'<div class="terminal-card">{st.session_state["geo_rep"]}</div>', unsafe_allow_html=True)

with tab4:
    st.subheader("High Impact Economic Events")
    render_economic_calendar()

with tab5:
    st.subheader("Live Market Data")
    asset_map = {
        "Bitcoin (BTC/USD)": "COINBASE:BTCUSD",
        "Dollar Index (DXY)": "TVC:DXY",
        "Gold (XAU/USD)": "OANDA:XAUUSD",
        "Crude Oil (WTI)": "TVC:USOIL",
        "EUR / USD": "FX:EURUSD",
        "GBP / USD": "FX:GBPUSD",
        "USD / JPY": "FX:USDJPY",
    }
    selected_label = st.selectbox("Select Asset Class:", list(asset_map.keys()))
    render_chart(asset_map[selected_label])
