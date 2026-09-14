import base64
import json
from datetime import datetime, timedelta
import pytz
import requests
import streamlit as st
from PIL import Image

# Page Configuration
st.set_page_config(
    page_title="Shawkat Prop Firm AI Challenge Manager",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# Security Password Check (Persisted via Query Params & Session State)
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    if st.query_params.get("unlocked") == "true":
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Restricted Prop Firm App Access")
    st.markdown("Please enter the security password to unlock **Shawkat Prop Firm AI Challenge Manager**:")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Unlock App", type="primary"):
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
    if "AUD" in asset_upper and "CAD" in asset_upper:
        return "🇦🇺🇨🇦"
    if "EUR" in asset_upper and "GBP" in asset_upper:
        return "🇪🇺🇬🇧"
    if "GBP" in asset_upper and "JPY" in asset_upper:
        return "🇬🇧🇯🇵"
    if "EUR" in asset_upper and "JPY" in asset_upper:
        return "🇪🇺🇯🇵"
    if "CAD" in asset_upper and "JPY" in asset_upper:
        return "🇨🇦🇯🇵"
    if "AUD" in asset_upper and "JPY" in asset_upper:
        return "🇦🇺🇯🇵"
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


def execute_with_fallbacks(api_key: str, messages: list, max_tokens: int = 550):
    cleaned_key = api_key.strip() if api_key else ""
    if not cleaned_key:
        raise Exception("Secret Key is missing or empty. Please enter your valid Secret Key in the sidebar.")

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
                    "X-OpenRouter-Title": "Shawkat Prop Firm AI App",
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


def generate_prop_vision_signal(api_key: str, image_bytes: bytes, account_balance: float, risk_pct: float):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    local_tz = pytz.timezone("Asia/Karachi")
    now_local = datetime.now(local_tz)
    current_local_time = now_local.strftime("%H:%M:%S")

    exact_risk_dollar = account_balance * (risk_pct / 100.0)

    prompt = f"""
    You are an elite institutional risk manager and prop firm trading mentor. Current local time is {current_local_time} (Asia/Karachi).
    The user's live verified balance is exactly ${account_balance:,.2f}. 
    The selected risk profile assigns a strict risk percentage of {risk_pct}%, meaning the exact maximum dollar risk must be calculated as ${exact_risk_dollar:,.2f}.
    
    Deeply analyze this chart screenshot. Provide a comprehensive institutional breakdown containing:
    1. The asset name or symbol visible on the chart.
    2. The market direction ("BUY" or "SELL").
    3. Precise Entry Price.
    4. Safe institutional Stop Loss (SL) level (avoiding premature stop hunts/wicks).
    5. High-probability Take Profit (TP) level adhering strictly to a 1:2 risk-to-reward ratio.
    6. Exact calculated dollar risk (${exact_risk_dollar:,.2f}).
    7. Suggested Lot Size mathematically matched to the Entry and SL distance to risk exactly ${exact_risk_dollar:,.2f}.
    8. Detailed structural reason/thesis for why this trade is taken (e.g. liquidity sweep, order block mitigation, structural shift).
    9. Estimated exact clock time when price is expected to reach/trigger the entry price (e.g. "Today at 16:45 PKT").
    10. Estimated exact clock time when price is expected to hit the Take Profit target (e.g. "Today at 19:30 PKT").

    CRITICAL INSTRUCTIONS:
    - Output ONLY valid raw JSON. Do NOT include markdown code blocks.
    - Provide exact keys: "asset", "live_price", "signal", "entry_price", "stop_loss_price", "take_profit_price", "risk_reward_ratio", "recommended_risk_amount", "suggested_lot_size", "accuracy", "reason", "estimated_entry_time", "estimated_tp_time".
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
    return execute_with_fallbacks(api_key, messages, max_tokens=550)


# ------------------------------------------------------------------------------
# Session State Initialization for Prop Firm
# ------------------------------------------------------------------------------
if "prop_active" not in st.session_state:
    st.session_state.prop_active = False
if "initial_balance" not in st.session_state:
    st.session_state.initial_balance = 10000.0
if "current_balance" not in st.session_state:
    st.session_state.current_balance = 10000.0
if "phase" not in st.session_state:
    st.session_state.phase = "Phase 1"
if "risk_per_trade" not in st.session_state:
    st.session_state.risk_per_trade = 1.0
if "profit_target" not in st.session_state:
    st.session_state.profit_target = 1000.0
if "max_daily_loss" not in st.session_state:
    st.session_state.max_daily_loss = 500.0
if "max_total_loss" not in st.session_state:
    st.session_state.max_total_loss = 1000.0
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
# Sidebar Configuration (Risk Profiles Instead of Raw Sliders)
# ------------------------------------------------------------------------------
st.sidebar.title("🛡️ Prop Control Panel")

api_key = st.sidebar.text_input("Secret Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Challenge Configuration")

selected_phase = st.sidebar.selectbox("Select Challenge Step", ["Phase 1", "Phase 2", "Funded Live Account"])
capital_choice = st.sidebar.selectbox("Account Size ($)", [5000, 10000, 25000, 50000, 100000], index=1)

risk_profile_choice = st.sidebar.selectbox(
    "Select Risk Strategy Profile", 
    [
        "🛡️ Low Risk (0.5% per trade — Safe & More Trades)", 
        "⚖️ Balanced (1.0% per trade — Prop Sweet Spot)", 
        "🚀 High Risk / Fast Finish (2.0% per trade — Aggressive)"
    ],
    index=1
)

if "Low Risk" in risk_profile_choice:
    assigned_risk_pct = 0.5
elif "High Risk" in risk_profile_choice:
    assigned_risk_pct = 2.0
else:
    assigned_risk_pct = 1.0

if st.sidebar.button("Initialize / Reset Challenge", type="primary"):
    cap = float(capital_choice)
    st.session_state.initial_balance = cap
    st.session_state.current_balance = cap
    st.session_state.phase = selected_phase
    st.session_state.risk_per_trade = assigned_risk_pct
    
    if selected_phase == "Phase 1":
        st.session_state.profit_target = cap * 0.10
    elif selected_phase == "Phase 2":
        st.session_state.profit_target = cap * 0.05
    else:
        st.session_state.profit_target = cap * 0.15

    st.session_state.max_daily_loss = cap * 0.05
    st.session_state.max_total_loss = cap * 0.10
    st.session_state.current_pnl = 0.0
    st.session_state.daily_pnl = 0.0
    st.session_state.trades_won = 0
    st.session_state.trades_lost = 0
    st.session_state.prop_active = True
    st.sidebar.success(f"Initialized {selected_phase} with {assigned_risk_pct}% Risk Profile!")

if st.session_state.prop_active:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Live Balance & Roadmap")
    st.sidebar.metric("AI Synchronized Balance", f"${st.session_state.current_balance:,.2f}")
    st.sidebar.markdown(f"*Active Risk Strategy: **{st.session_state.risk_per_trade}%** per trade (${st.session_state.current_balance * (st.session_state.risk_per_trade / 100.0):,.2f})*")

# ------------------------------------------------------------------------------
# Main App Layout
# ------------------------------------------------------------------------------
st.title("🛡️ Shawkat Prop Firm AI Challenge Manager")

if not api_key or not api_key.strip():
    st.warning("⚠️ Please enter your Secret Key in the sidebar to activate the challenge manager.")
    st.stop()

if not st.session_state.prop_active:
    st.info("👈 Please select your risk strategy profile and initialize your Prop Challenge from the sidebar.")
    st.stop()

# Safety Check
if st.session_state.current_pnl >= st.session_state.profit_target:
    st.success(f"🎉 **CONGRATULATIONS! {st.session_state.phase} PROFIT TARGET ACHIEVED!**")
    st.stop()

if st.session_state.daily_pnl <= -st.session_state.max_daily_loss:
    st.error(f"🛑 **DAILY DRAWDOWN LIMIT HIT (-${st.session_state.max_daily_loss:,.2f})!** Trading locked for today.")
    st.stop()

# Main Workspace Tabs
tab1, tab2 = st.tabs(["1️⃣ Live Screenshot Analyzer & Balance Sync", "2️⃣ Log Trade & Type Exact Balance"])

# ------------------------------------------------------------------------------
# Tab 1: Screenshot Analyzer with AI Always Informed of Exact Balance
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("AI Vision Chart Analyzer (Fully Synced)")
    
    col_bal_1, col_bal_2 = st.columns([2, 2])
    with col_bal_1:
        st.session_state.current_balance = st.number_input(
            "Exact Balance Sent to AI ($)", 
            min_value=10.0, 
            max_value=1000000.0, 
            value=float(st.session_state.current_balance),
            step=10.0,
            help="The AI uses this balance and your profile risk setting in real-time."
        )
    with col_bal_2:
        st.metric("Active Risk Capital", f"${st.session_state.current_balance:,.2f}", f"{st.session_state.risk_per_trade}% Profile Risk")

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload Chart Screenshot", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Market Setup", use_container_width=True)

        if st.button("Generate AI Signal with Profile Risk Sizing", type="primary"):
            with st.spinner("AI is analyzing chart structure, timing projections, and risk parameters..."):
                try:
                    img_bytes = uploaded_file.getvalue()
                    sig = generate_prop_vision_signal(
                        api_key, 
                        img_bytes, 
                        st.session_state.current_balance, 
                        st.session_state.risk_per_trade
                    )
                    st.session_state.last_signal = sig
                except Exception as e:
                    st.error(str(e))

# ------------------------------------------------------------------------------
# Tab 2: Log Trade Result & Type Exact Balance Manually
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Log Closed Trade & Enter Exact Final Balance")
    
    st.markdown("When your trade finishes, type your **exact account balance** below so the AI stays fully informed and synchronized for your next screenshot upload.")

    col_log1, col_log2 = st.columns(2)
    
    current_risk_pct = st.session_state.risk_per_trade
    estimated_gain = st.session_state.current_balance * (current_risk_pct / 100.0) * 2.0
    estimated_loss = st.session_state.current_balance * (current_risk_pct / 100.0)

    with col_log1:
        st.markdown("#### ✅ Winning Trade Log")
        suggested_win_balance = st.session_state.current_balance + estimated_gain
        exact_win_balance_input = st.number_input(
            "Type Exact Balance After Win ($)",
            min_value=10.0,
            max_value=1000000.0,
            value=float(suggested_win_balance),
            step=10.0,
            key="win_balance_input"
        )
        if st.button("Confirm & Save Winning Trade", type="primary", use_container_width=True):
            diff = exact_win_balance_input - st.session_state.current_balance
            st.session_state.current_balance = exact_win_balance_input
            st.session_state.current_pnl += diff
            st.session_state.daily_pnl += diff
            st.session_state.trades_won += 1
            st.success(f"Saved! Balance updated to exact ${exact_win_balance_input:,.2f}. AI is fully informed.")
            st.rerun()

    with col_log2:
        st.markdown("#### ❌ Losing Trade Log")
        suggested_loss_balance = max(10.0, st.session_state.current_balance - estimated_loss)
        exact_loss_balance_input = st.number_input(
            "Type Exact Balance After Loss ($)",
            min_value=10.0,
            max_value=1000000.0,
            value=float(suggested_loss_balance),
            step=10.0,
            key="loss_balance_input"
        )
        if st.button("Confirm & Save Losing Trade", type="secondary", use_container_width=True):
            diff = st.session_state.current_balance - exact_loss_balance_input
            st.session_state.current_balance = exact_loss_balance_input
            st.session_state.current_pnl -= diff
            st.session_state.daily_pnl -= diff
            st.session_state.trades_lost += 1
            st.error(f"Saved! Balance updated to exact ${exact_loss_balance_input:,.2f}. AI is fully informed.")
            st.rerun()

    st.markdown("---")
    st.metric("Current Synchronized Balance in System", f"${st.session_state.current_balance:,.2f}")

# ------------------------------------------------------------------------------
# Display Active Signal Output Area with Timing & Thesis
# ------------------------------------------------------------------------------
if st.session_state.last_signal:
    st.markdown("---")
    sig_data = st.session_state.last_signal
    asset_flag = get_pair_flag(sig_data.get("asset", "EUR/USD"))
    signal_dir = sig_data.get("signal", "BUY").upper()

    signal_color = "green" if signal_dir == "BUY" else "red"
    signal_icon = "🟢 🚀 BUY" if signal_dir == "BUY" else "🔴 📉 SELL"

    st.markdown(f"## {asset_flag} **Asset:** `{sig_data.get('asset')}`")

    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.markdown(f"### Direction: :{signal_color}[{signal_icon}]")
        st.write(f"**Best Safe Entry Price:** `{sig_data.get('entry_price')}`")
        st.write(f"**Stop Loss (SL - Wick Protected):** 🛡️ `{sig_data.get('stop_loss_price')}`")
        st.write(f"**Take Profit (TP):** 🎯 `{sig_data.get('take_profit_price')}`")
        st.write(f"**Risk-to-Reward (R:R):** `{sig_data.get('risk_reward_ratio')}`")
        st.write(f"**Estimated Entry Time:** ⏰ `{sig_data.get('estimated_entry_time', 'N/A')}`")
        st.write(f"**Estimated TP Hit Time:** 🎯 `{sig_data.get('estimated_tp_time', 'N/A')}`")

    with res_col2:
        st.write(f"**Exact Dollar Risk Amount:** `${sig_data.get('recommended_risk_amount')}`")
        st.write(f"**Suggested Lot Size:** 📦 `{sig_data.get('suggested_lot_size')}`")
        st.write(f"**Win Accuracy Score:** `{sig_data.get('accuracy')}`")

    st.markdown("---")
    st.markdown("### 🧠 Institutional Trade Thesis & Reason")
    st.info(sig_data.get('reason', 'No specific reason provided.'))
