import base64
import json
from datetime import datetime
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


def execute_with_fallbacks(api_key: str, messages: list, max_tokens: int = 400):
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

    max_risk_amount = account_balance * (risk_pct / 100.0)

    prompt = f"""
    You are an elite institutional risk manager and prop firm trading mentor. Current local time is {current_local_time}.
    The user is trading a ${account_balance:,.2f} Prop Firm Challenge account. Max allowed risk per trade is {risk_pct}% (${max_risk_amount:.2f}).
    Deeply analyze this chart screenshot. Provide the absolute best precision entry price, a safe institutional Stop Loss (SL) level that avoids premature wicks/hunting, and a high-probability Take Profit (TP) level ensuring a minimum 1:2 risk-to-reward ratio.

    CRITICAL INSTRUCTIONS:
    - Output ONLY valid raw JSON. Do NOT include markdown code blocks.
    - Provide exact keys: "asset", "live_price", "signal", "entry_price", "stop_loss_price", "take_profit_price", "risk_reward_ratio", "recommended_risk_amount", "suggested_lot_size", "accuracy", "reason".
    - "signal" must be strictly either "BUY" or "SELL".
    - "entry_price", "stop_loss_price", and "take_profit_price" must be realistic floating-point numbers based on the chart prices.
    - "recommended_risk_amount" must equal exactly ${max_risk_amount:.2f} or lower.
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
    return execute_with_fallbacks(api_key, messages, max_tokens=450)


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
if "profit_target" not in st.session_state:
    st.session_state.profit_target = 1000.0  # 10% for Phase 1
if "max_daily_loss" not in st.session_state:
    st.session_state.max_daily_loss = 500.0  # 5% daily limit
if "max_total_loss" not in st.session_state:
    st.session_state.max_total_loss = 1000.0 # 10% total drawdown limit
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
# Sidebar Configuration
# ------------------------------------------------------------------------------
st.sidebar.title("🛡️ Prop Control Panel")

api_key = st.sidebar.text_input("Secret Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Challenge Configuration")

selected_phase = st.sidebar.selectbox("Select Challenge Step", ["Phase 1", "Phase 2", "Funded Live Account"])
capital_choice = st.sidebar.selectbox("Account Size ($)", [5000, 10000, 25000, 50000, 100000], index=1)
risk_per_trade = st.sidebar.slider("Max Risk Per Trade (%)", 0.25, 2.0, 1.0, 0.25)

if st.sidebar.button("Initialize / Reset Challenge", type="primary"):
    cap = float(capital_choice)
    st.session_state.initial_balance = cap
    st.session_state.current_balance = cap
    st.session_state.phase = selected_phase
    
    if selected_phase == "Phase 1":
        st.session_state.profit_target = cap * 0.10  # 10% target for Phase 1
    elif selected_phase == "Phase 2":
        st.session_state.profit_target = cap * 0.05  # 5% target for Phase 2
    else:
        st.session_state.profit_target = cap * 0.15  # Funded growth goal

    st.session_state.max_daily_loss = cap * 0.05   # 5% daily loss limit
    st.session_state.max_total_loss = cap * 0.10   # 10% max total loss limit
    st.session_state.current_pnl = 0.0
    st.session_state.daily_pnl = 0.0
    st.session_state.trades_won = 0
    st.session_state.trades_lost = 0
    st.session_state.prop_active = True
    st.sidebar.success(f"Initialized {selected_phase} (${cap:,.2f})!")

if st.session_state.prop_active:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Multi-Trade Roadmap")
    
    # Calculate how many 1:2 R:R trades are needed
    risk_dollar_per_trade = st.session_state.initial_balance * (risk_per_trade / 100.0)
    reward_dollar_per_win = risk_dollar_per_trade * 2.0  # Assuming 1:2 R:R
    
    remaining_target = max(0.0, st.session_state.profit_target - st.session_state.current_pnl)
    trades_needed_est = int((remaining_target / reward_dollar_per_win) + 0.99) if reward_dollar_per_win > 0 else 0
    
    st.sidebar.metric("Account Balance", f"${st.session_state.current_balance:,.2f}")
    st.sidebar.metric("Target Profit Needed", f"${remaining_target:,.2f}")
    st.sidebar.metric("Estimated Wins Needed (1:2 R:R)", f"{trades_needed_est} clean wins")
    st.sidebar.markdown(f"*Each clean win at {risk_per_trade}% risk adds ~**${reward_dollar_per_win:,.2f}** profit.*")
    
    st.sidebar.markdown("---")
    st.sidebar.metric("Daily PnL", f"${st.session_state.daily_pnl:,.2f}")
    st.sidebar.metric("Max Daily Loss Room", f"${st.session_state.max_daily_loss + st.session_state.daily_pnl:,.2f}")

# ------------------------------------------------------------------------------
# Main App Layout
# ------------------------------------------------------------------------------
st.title("🛡️ Shawkat Prop Firm AI Challenge Manager")

if not api_key or not api_key.strip():
    st.warning("⚠️ Please enter your Secret Key in the sidebar to activate the challenge manager.")
    st.stop()

if not st.session_state.prop_active:
    st.info("👈 Please configure and initialize your Prop Challenge parameters from the sidebar.")
    st.stop()

# Safety Drawdown Lock Checks
if st.session_state.current_pnl >= st.session_state.profit_target:
    st.success(f"🎉 **CONGRATULATIONS! {st.session_state.phase} PROFIT TARGET ACHIEVED!**")
    st.stop()

if st.session_state.daily_pnl <= -st.session_state.max_daily_loss:
    st.error(f"🛑 **DAILY DRAWDOWN LIMIT HIT (-${st.session_state.max_daily_loss:,.2f})!** Trading locked for today to protect your account.")
    st.stop()

if (st.session_state.initial_balance - st.session_state.current_balance) >= st.session_state.max_total_loss:
    st.error("🛑 **MAX TOTAL DRAWDOWN BREACHED!** Challenge failed. Reset capital in the sidebar to try again.")
    st.stop()

# Main Workspace Tabs
tab1, tab2 = st.tabs(["1️⃣ Precision Entry & SL/TP Analyzer", "2️⃣ Multi-Trade Roadmap & PnL Log"])

# ------------------------------------------------------------------------------
# Tab 1: Screenshot Analyzer for Prop Trades with SL/TP
# ------------------------------------------------------------------------------
with tab1:
    st.subheader(f"Precision Setup Analyzer — {st.session_state.phase} (${st.session_state.current_balance:,.2f} Balance)")
    uploaded_file = st.file_uploader("Upload Chart Screenshot", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Market Setup", use_container_width=True)

        if st.button("Calculate Best Safe Entry, SL & TP", type="primary"):
            with st.spinner("AI is analyzing trend structure, avoiding wicks, and calculating optimal SL/TP..."):
                try:
                    img_bytes = uploaded_file.getvalue()
                    sig = generate_prop_vision_signal(
                        api_key, 
                        img_bytes, 
                        st.session_state.current_balance, 
                        risk_per_trade
                    )
                    st.session_state.last_signal = sig
                except Exception as e:
                    st.error(str(e))

# ------------------------------------------------------------------------------
# Tab 2: Roadmap & PnL Log
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Challenge Progress & Multi-Trade Roadmap")
    
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    col_p1.metric("Starting Balance", f"${st.session_state.initial_balance:,.2f}")
    col_p2.metric("Total PnL", f"${st.session_state.current_pnl:,.2f}")
    col_p3.metric("Win / Loss Count", f"🟢 {st.session_state.trades_won} W / 🔴 {st.session_state.trades_lost} L")
    col_p4.metric("Target Goal", f"${st.session_state.profit_target:,.2f}")

    st.markdown("---")
    st.write("Record your trade results to dynamically progress through your multi-trade challenge roadmap:")
    
    col_btn1, col_btn2 = st.columns(2)
    trade_gain_dollar = st.session_state.initial_balance * (risk_per_trade / 100.0) * 2.0 # 1:2 Reward

    if col_btn1.button("✅ Log Winning Trade (+2.0R Profit)", type="secondary", use_container_width=True):
        gain = trade_gain_dollar
        st.session_state.current_balance += gain
        st.session_state.current_pnl += gain
        st.session_state.daily_pnl += gain
        st.session_state.trades_won += 1
        st.success(f"Logged win! Added +${gain:,.2f} to account.")
        st.rerun()

    if col_btn2.button("❌ Log Losing Trade (-1.0R Risk)", type="secondary", use_container_width=True):
        loss = st.session_state.initial_balance * (risk_per_trade / 100.0)
        st.session_state.current_balance -= loss
        st.session_state.current_pnl -= loss
        st.session_state.daily_pnl -= loss
        st.session_state.trades_lost += 1
        st.error(f"Logged loss. Deducted -${loss:,.2f} from account.")
        st.rerun()

# ------------------------------------------------------------------------------
# Display Active Signal Output Area with Exact SL & TP
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

    with res_col2:
        st.write(f"**Suggested Lot Size:** `{sig_data.get('suggested_lot_size')}`")
        st.write(f"**Max Risk Amount:** `${sig_data.get('recommended_risk_amount')}`")
        st.write(f"**Win Accuracy Score:** `{sig_data.get('accuracy')}`")

    st.caption(f"**Institutional Reason & Structure:** {sig_data.get('reason')}")
