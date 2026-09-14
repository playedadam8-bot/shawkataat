import base64
import json
from datetime import datetime, timedelta
import pytz
import requests
import streamlit as st
from PIL import Image

# Page Configuration
st.set_page_config(
    page_title="Funding Pips $5K Challenge AI Multi-TP Bot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# Persistent Session State Initialization (Survives Browser Refreshes)
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    if st.query_params.get("unlocked") == "true":
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "prop_active" not in st.session_state:
    st.session_state.prop_active = False
if "initial_balance" not in st.session_state:
    st.session_state.initial_balance = 5000.0
if "current_balance" not in st.session_state:
    st.session_state.current_balance = 5000.0
if "phase" not in st.session_state:
    st.session_state.phase = "Phase 1"
if "risk_per_trade" not in st.session_state:
    st.session_state.risk_per_trade = 1.0
if "profit_target" not in st.session_state:
    st.session_state.profit_target = 400.0  # 8% of $5,000
if "max_daily_loss" not in st.session_state:
    st.session_state.max_daily_loss = 250.0  # 5% of $5,000
if "max_total_loss" not in st.session_state:
    st.session_state.max_total_loss = 500.0  # 10% of $5,000
if "min_trading_days" not in st.session_state:
    st.session_state.min_trading_days = 3
if "trading_days_completed" not in st.session_state:
    st.session_state.trading_days_completed = 0
if "current_pnl" not in st.session_state:
    st.session_state.current_pnl = 0.0
if "daily_pnl" not in st.session_state:
    st.session_state.daily_pnl = 0.0
if "trades_won" not in st.session_state:
    st.session_state.trades_won = 0
if "trades_lost" not in st.session_state:
    st.session_state.trades_lost = 0
if "last_signal" not in st.session_state:
    st.session_state.last_signal = None

# ------------------------------------------------------------------------------
# Security Password Check
# ------------------------------------------------------------------------------
if not st.session_state.authenticated:
    st.title("🔒 Restricted Funding Pips Bot Access")
    st.markdown("Please enter the security password to unlock your **$5K Funding Pips Multi-TP Bot**:")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Unlock Bot", type="primary"):
        if password_input == "shawkatedeveloper":
            st.session_state.authenticated = True
            st.query_params["unlocked"] = "true"
            st.success("Access granted!")
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()

# ------------------------------------------------------------------------------
# Helper Functions & Safe Fallback API Executor
# ------------------------------------------------------------------------------

def get_pair_flag(asset_name: str) -> str:
    asset_upper = asset_name.upper()
    if "EUR" in asset_upper and "USD" in asset_upper:
        return "🇪🇺🇺🇸"
    if "GBP" in asset_upper and "USD" in asset_upper:
        return "🇬🇧🇺🇸"
    if "USD" in asset_upper and "JPY" in asset_upper:
        return "🇺🇸🇯🇵"
    if "XAU" in asset_upper or "GOLD" in asset_upper:
        return "🥇"
    if "BTC" in asset_upper or "CRYPTO" in asset_upper:
        return "🪙"
    if "OTC" in asset_upper:
        return "🌐"
    return "📊"


def parse_json_response(raw_content: str) -> dict:
    content = raw_content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    if "{" in content and "}" in content:
        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1
        content = content[start_idx:end_idx]

    return json.loads(content)


def execute_with_fallbacks(api_key: str, messages: list, max_tokens: int = 750):
    cleaned_key = api_key.strip() if api_key else ""
    if not cleaned_key:
        raise Exception("Secret Key is missing or empty. Please enter your valid OpenRouter Key in the sidebar.")

    fallback_models = [
        "openai/gpt-4o",          # High Accuracy / ChatGPT
        "deepseek/deepseek-chat", # Fast & Reliable Mid-tier
        "google/gemini-2.5-flash" # Lightweight / Backup Vision & Text
    ]
    
    last_error = ""
    for model_id in fallback_models:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {cleaned_key}",
                    "HTTP-Referer": "https://streamlit.app",
                    "X-OpenRouter-Title": "Funding Pips 5K Multi-TP Bot",
                },
                json={
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                },
                timeout=30,
            )

            if response.status_code == 200:
                res_json = response.json()
                if "choices" in res_json and len(res_json["choices"]) > 0:
                    raw_text = res_json["choices"][0]["message"]["content"]
                    return parse_json_response(raw_text)
                else:
                    last_error = f"Model {model_id} returned empty choices: {response.text}"
            else:
                last_error = f"Model {model_id} failed with status {response.status_code}: {response.text}"
        except Exception as e:
            last_error = f"Model {model_id} error: {str(e)}"
            continue
            
    raise Exception(f"All fallback models failed. Last error: {last_error}")


def generate_funding_pips_signal(api_key: str, image_bytes: bytes, account_balance: float, risk_pct: float, current_phase: str):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    local_tz = pytz.timezone("Asia/Karachi")
    now_local = datetime.now(local_tz)
    current_local_time = now_local.strftime("%H:%M:%S")

    exact_risk_dollar = account_balance * (risk_pct / 100.0)

    prompt = f"""
    You are an elite prop firm trading bot configured specifically for Funding Pips $5,000 account ({current_phase}). Current local time is {current_local_time} (Asia/Karachi).
    The user's live verified balance is exactly ${account_balance:,.2f}. 
    The risk profile assigns a strict risk percentage of {risk_pct}%, meaning maximum dollar risk per trade is exactly ${exact_risk_dollar:,.2f}.
    
    CRITICAL REQUIREMENT FOR TAKE PROFITS: 
    Do NOT give just one long distant Take Profit. Instead, provide **4 progressive Take Profit levels (TP1, TP2, TP3, TP4)** scaled smartly across structural support/resistance zones so the trader can easily scale out partials and hit quick wins safely.
    
    Deeply analyze this chart screenshot and provide a comprehensive institutional breakdown containing:
    1. The asset name or symbol visible on the chart.
    2. The market direction ("BUY" or "SELL").
    3. Precise Entry Price.
    4. Safe institutional Stop Loss (SL) level (avoiding stop hunts, keeping risk within rules).
    5. Four progressive Take Profit targets:
       - "tp1": Early scalp target (quick partial take-profit)
       - "tp2": Mid-range structural target
       - "tp3": Extended trend target
       - "tp4": Final maximum target
    6. Exact calculated dollar risk (${exact_risk_dollar:,.2f}).
    7. Suggested Lot Size mathematically matched to the Entry and SL distance to risk exactly ${exact_risk_dollar:,.2f}.
    8. Detailed structural reason/thesis for why this trade is taken.
    9. Estimated exact clock time when price is expected to hit Entry, TP1, TP2, TP3, and TP4.
    10. Setup Confidence Score on an integer scale from 0 to 10 (where 10 is an A+ pristine setup).

    CRITICAL INSTRUCTIONS:
    - Output ONLY valid raw JSON. Do NOT include markdown code blocks.
    - Provide exact keys: "asset", "live_price", "signal", "entry_price", "stop_loss_price", "tp1", "tp2", "tp3", "tp4", "risk_reward_ratio", "recommended_risk_amount", "suggested_lot_size", "setup_score", "reason", "estimated_entry_time", "estimated_tp1_time", "estimated_tp2_time", "estimated_tp3_time", "estimated_tp4_time".
    - "signal" must be strictly either "BUY" or "SELL".
    """

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    },
                },
            ],
        }
    ]
    return execute_with_fallbacks(api_key, messages, max_tokens=750)


# ------------------------------------------------------------------------------
# Sidebar Configuration ($5K Funding Pips Parameters & API Key)
# ------------------------------------------------------------------------------
st.sidebar.title("🎯 Funding Pips $5K Bot")

# Persistent OpenRouter API Key Input
st.session_state.api_key = st.sidebar.text_input(
    "OpenRouter Secret Key", 
    value=st.session_state.api_key, 
    type="password",
    help="Enter your OpenRouter key to power the AI vision analyzer."
)

st.sidebar.markdown("---")
st.sidebar.subheader("📋 Funding Pips $5K Parameters")

selected_phase_choice = st.sidebar.selectbox(
    "Select Challenge Stage", 
    [
        "Phase 1 (Target: 8% = $400 | Min Days: 3)", 
        "Phase 2 (Target: 5% = $250 | Min Days: 3)", 
        "Funded Master Account"
    ],
    index=0
)

risk_profile_choice = st.sidebar.selectbox(
    "Select Risk Strategy Profile", 
    [
        "🛡️ Conservative (0.5% per trade = $25 risk)", 
        "⚖️ Balanced Prop Sweet Spot (1.0% per trade = $50 risk)", 
        "🚀 Fast Finish Aggressive (2.0% per trade = $100 risk)"
    ],
    index=1
)

if "Conservative" in risk_profile_choice:
    assigned_risk_pct = 0.5
elif "Fast Finish" in risk_profile_choice:
    assigned_risk_pct = 2.0
else:
    assigned_risk_pct = 1.0

if st.sidebar.button("Initialize / Reset $5K Bot", type="primary"):
    st.session_state.initial_balance = 5000.0
    st.session_state.current_balance = 5000.0
    st.session_state.risk_per_trade = assigned_risk_pct
    
    if "Phase 1" in selected_phase_choice:
        st.session_state.phase = "Phase 1"
        st.session_state.profit_target = 400.0  # 8%
        st.session_state.min_trading_days = 3
    elif "Phase 2" in selected_phase_choice:
        st.session_state.phase = "Phase 2"
        st.session_state.profit_target = 250.0  # 5%
        st.session_state.min_trading_days = 3
    else:
        st.session_state.phase = "Funded Master Account"
        st.session_state.profit_target = 750.0
        st.session_state.min_trading_days = 0

    st.session_state.max_daily_loss = 250.0   # 5% strict daily drawdown
    st.session_state.max_total_loss = 500.0   # 10% max overall drawdown
    st.session_state.current_pnl = 0.0
    st.session_state.daily_pnl = 0.0
    st.session_state.trading_days_completed = 0
    st.session_state.trades_won = 0
    st.session_state.trades_lost = 0
    st.session_state.prop_active = True
    st.sidebar.success("Funding Pips $5K Bot successfully initialized!")

if st.session_state.prop_active:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Live Account Metrics")
    st.sidebar.metric("Synchronized Balance", f"${st.session_state.current_balance:,.2f}")
    st.sidebar.markdown(f"*Stage: **{st.session_state.phase}***")
    st.sidebar.markdown(f"*Target: **${st.session_state.profit_target:,.2f}***")
    st.sidebar.markdown(f"*Daily Limit: **-$250.00 (5%)***")
    st.sidebar.markdown(f"*Max Loss Limit: **-$500.00 (10%)***")
    st.sidebar.markdown(f"*Min Days Done: **{st.session_state.trading_days_completed} / {st.session_state.min_trading_days}***")

# ------------------------------------------------------------------------------
# Main App Interface
# ------------------------------------------------------------------------------
st.title("🎯 Funding Pips $5K Challenge Multi-TP AI Bot")

current_api_key = st.session_state.api_key

if not current_api_key or not current_api_key.strip():
    st.warning("⚠️ Please enter your OpenRouter Secret Key in the sidebar to activate the bot.")
    st.stop()

if not st.session_state.prop_active:
    st.info("👈 Please select your risk profile and click **Initialize / Reset $5K Bot** in the sidebar to start.")
    st.stop()

# Rule Enforcement Checks
if st.session_state.current_pnl >= st.session_state.profit_target and st.session_state.trading_days_completed >= st.session_state.min_trading_days:
    st.success(f"🎉 **CONGRATULATIONS! FUNDING PIPS {st.session_state.phase} COMPLETED SUCCESSFULLY!**")
    st.stop()
elif st.session_state.current_pnl >= st.session_state.profit_target:
    st.warning(f"⚠️ **Profit target reached (${st.session_state.current_pnl:,.2f}), but you need {st.session_state.min_trading_days} minimum trading days!** Currently completed: {st.session_state.trading_days_completed} days. Place small compliant trades to fulfill the day requirement.")

if st.session_state.daily_pnl <= -st.session_state.max_daily_loss:
    st.error(f"🛑 **DAILY DRAWDOWN LIMIT HIT (-$250.00 / 5%)!** Trading locked for today to protect your $5K challenge.")
    st.stop()

# Tabs
tab1, tab2 = st.tabs(["1️⃣ Multi-TP Chart Scanner & Signal Generator", "2️⃣ Log Trade & Sync $5K Balance"])

# ------------------------------------------------------------------------------
# Tab 1: Chart Scanner & Multi-TP Signal Generator
# ------------------------------------------------------------------------------
with tab1:
    st.subheader(f"Funding Pips $5K Multi-TP Signal Generator ({st.session_state.phase})")
    st.markdown("Upload your chart screenshot. The AI will map **4 progressive Take Profit levels (TP1 to TP4)** so you can easily scale out, secure partial profits, and hit your target safely.")

    col_b1, col_b2 = st.columns([2, 2])
    with col_b1:
        st.session_state.current_balance = st.number_input(
            "Live Account Balance ($)", 
            min_value=4500.0, 
            max_value=10000.0, 
            value=float(st.session_state.current_balance),
            step=10.0,
            help="Automatically updated by your trade logs or set manually."
        )
    with col_b2:
        st.metric("Active Risk Per Trade", f"${st.session_state.current_balance * (st.session_state.risk_per_trade / 100.0):,.2f}", f"{st.session_state.risk_per_trade}% Risk")

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload Market Chart Screenshot", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Funding Pips Setup Analysis", use_container_width=True)

        if st.button("Generate Multi-TP Signals (TP1-TP4)", type="primary"):
            with st.spinner("AI is analyzing chart structure and calculating 4 progressive Take Profit targets..."):
                try:
                    img_bytes = uploaded_file.getvalue()
                    sig = generate_funding_pips_signal(
                        current_api_key, 
                        img_bytes, 
                        st.session_state.current_balance, 
                        st.session_state.risk_per_trade,
                        st.session_state.phase
                    )
                    st.session_state.last_signal = sig
                except Exception as e:
                    st.error(str(e))

# ------------------------------------------------------------------------------
# Tab 2: Trade Logger & Balance Sync
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Log Closed Trade & Update $5K Balance")
    st.markdown("Keep your account balance accurately synchronized after every trade and increment your trading days to satisfy the minimum 3-day rule.")

    # Option to manually add a trading day if they placed a trade today
    col_day1, col_day2 = st.columns([2, 2])
    with col_day1:
        st.write(f"**Trading Days Completed:** `{st.session_state.trading_days_completed} / {st.session_state.min_trading_days}`")
    with col_day2:
        if st.button("➕ Mark Today as a Completed Trading Day"):
            st.session_state.trading_days_completed += 1
            st.success(f"Day logged! Total completed days: {st.session_state.trading_days_completed}")
            st.rerun()

    st.markdown("---")
    col_l1, col_l2 = st.columns(2)
    
    current_risk_dollar = st.session_state.current_balance * (st.session_state.risk_per_trade / 100.0)
    suggested_win_gain = current_risk_dollar * 2.0

    with col_l1:
        st.markdown("#### ✅ Winning Trade Log")
        win_bal_input = st.number_input(
            "Exact Balance After Win ($)",
            min_value=4500.0,
            max_value=10000.0,
            value=float(st.session_state.current_balance + suggested_win_gain),
            step=5.0,
            key="win_bal_field"
        )
        if st.button("Save Winning Trade & Count Day", type="primary", use_container_width=True):
            diff = win_bal_input - st.session_state.current_balance
            st.session_state.current_balance = win_bal_input
            st.session_state.current_pnl += diff
            st.session_state.daily_pnl += diff
            st.session_state.trades_won += 1
            if st.session_state.trading_days_completed < st.session_state.min_trading_days:
                st.session_state.trading_days_completed += 1
            st.success(f"Saved! Balance updated to ${win_bal_input:,.2f}. Day automatically counted.")
            st.rerun()

    with col_l2:
        st.markdown("#### ❌ Losing Trade Log")
        loss_bal_input = st.number_input(
            "Exact Balance After Loss ($)",
            min_value=4500.0,
            max_value=10000.0,
            value=float(max(4500.0, st.session_state.current_balance - current_risk_dollar)),
            step=5.0,
            key="loss_bal_field"
        )
        if st.button("Save Losing Trade & Count Day", type="secondary", use_container_width=True):
            diff = st.session_state.current_balance - loss_bal_input
            st.session_state.current_balance = loss_bal_input
            st.session_state.current_pnl -= diff
            st.session_state.daily_pnl -= diff
            st.session_state.trades_lost += 1
            if st.session_state.trading_days_completed < st.session_state.min_trading_days:
                st.session_state.trading_days_completed += 1
            st.error(f"Saved! Balance updated to ${loss_bal_input:,.2f}. Day automatically counted.")
            st.rerun()

    st.markdown("---")
    st.metric("System Synchronized Balance", f"${st.session_state.current_balance:,.2f}")

# ------------------------------------------------------------------------------
# Display Multi-TP Signal Card Output
# ------------------------------------------------------------------------------
if st.session_state.last_signal:
    st.markdown("---")
    sig = st.session_state.last_signal
    flag = get_pair_flag(sig.get("asset", "EUR/USD"))
    direction = sig.get("signal", "BUY").upper()
    color = "green" if direction == "BUY" else "red"
    icon = "🟢 🚀 BUY" if direction == "BUY" else "🔴 📉 SELL"

    st.markdown(f"## {flag} **Asset:** `{sig.get('asset')}`")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### Direction: :{color}[{icon}]")
        st.write(f"**Entry Price:** `{sig.get('entry_price')}` (⏰ `{sig.get('estimated_entry_time', 'N/A')}`)")
        st.write(f"**Stop Loss (SL):** 🛡️ `{sig.get('stop_loss_price')}`")
        st.markdown("#### 🎯 Multi-TP Targets (Scale Out Strategy)")
        st.write(f"* **TP1 (Quick Scalp - Secure Partials):** `{sig.get('tp1')}` (⏰ `{sig.get('estimated_tp1_time', 'N/A')}`)")
        st.write(f"* **TP2 (Mid Target):** `{sig.get('tp2')}` (⏰ `{sig.get('estimated_tp2_time', 'N/A')}`)")
        st.write(f"* **TP3 (Extended):** `{sig.get('tp3')}` (⏰ `{sig.get('estimated_tp3_time', 'N/Up')}`)")
        st.write(f"* **TP4 (Final Target):** `{sig.get('tp4')}` (⏰ `{sig.get('estimated_tp4_time', 'N/A')}`)")

    with c2:
        st.write(f"**Exact Dollar Risk:** `${sig.get('recommended_risk_amount')}`")
        st.write(f"**Suggested Lot Size:** 📦 `{sig.get('suggested_lot_size')}`")
        st.write(f"**A+ Setup Score (0-10):** ⭐ `{sig.get('setup_score', 'N/A')}/10`")
        st.write(f"**Risk-to-Reward:** `{sig.get('risk_reward_ratio', 'Multi-TP Scaled')}`")

    st.markdown("---")
    st.markdown("### 🧠 Institutional Trade Thesis & Reason")
    st.info(sig.get('reason', 'No specific reason provided.'))
