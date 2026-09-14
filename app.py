import base64
import json
import math
from datetime import datetime
import pytz
import requests
import streamlit as st
from PIL import Image

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="Shawkat Prop Firm AI Challenge Manager",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# FUNDINGPIPS $5K 2-STEP STANDARD SETTINGS
# ==============================================================================

ACCOUNT_SIZE = 5000.0

PHASE_1_TARGET = 400.0       # 8%
PHASE_2_TARGET = 250.0       # 5%

DAILY_LOSS_LIMIT = 250.0     # 5%
MAX_TOTAL_LOSS = 500.0       # 10%

RISK_PERCENT = 0.5           # 0.5% per trade
MAX_TRADES_PER_DAY = 3

DEFAULT_RR = 2.0

# Standard FX contract assumption:
# 1.00 lot = 100,000 units
FX_CONTRACT_SIZE = 100000

# Gold contract assumption:
# 1.00 lot = 100 oz
GOLD_CONTRACT_SIZE = 100


# ==============================================================================
# SUPPORTED MARKETS
# ==============================================================================

SUPPORTED_PAIRS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
    "GBPCHF",
    "EURCHF",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "AUDCAD",
    "AUDNZD",
    "NZDJPY",
    "EURAUD",
    "EURNZD",
    "GBPAUD",
    "GBPCAD",
    "GBPNZD",
    "AUDCHF",
    "CADCHF",
    "NZDCHF",
    "XAUUSD",
]


# ==============================================================================
# SESSION STATE
# ==============================================================================

defaults = {
    "authenticated": False,
    "api_key": "",
    "prop_active": False,

    "initial_balance": ACCOUNT_SIZE,
    "current_balance": ACCOUNT_SIZE,

    "phase": "Phase 1",

    "risk_per_trade": RISK_PERCENT,

    "profit_target": PHASE_1_TARGET,

    "max_daily_loss": DAILY_LOSS_LIMIT,
    "max_total_loss": MAX_TOTAL_LOSS,

    "max_trades_per_day": MAX_TRADES_PER_DAY,
    "trades_today": 0,

    "current_pnl": 0.0,
    "daily_pnl": 0.0,

    "trades_won": 0,
    "trades_lost": 0,

    "last_signal": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==============================================================================
# AUTHENTICATION
# ==============================================================================

if not st.session_state.authenticated:

    st.title("🔒 Restricted Prop Firm App Access")

    st.markdown(
        "Enter the security password to unlock "
        "**Shawkat Prop Firm AI Challenge Manager**."
    )

    password_input = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Unlock App", type="primary"):

        if password_input == "shawkatedeveloper":

            st.session_state.authenticated = True
            st.query_params["unlocked"] = "true"

            st.success("Access granted!")
            st.rerun()

        else:
            st.error("Incorrect password.")

    st.stop()


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_pair_flag(asset_name: str) -> str:

    asset = asset_name.upper().replace("/", "")

    if "XAU" in asset or "GOLD" in asset:
        return "🥇"

    flags = {
        "EURUSD": "🇪🇺🇺🇸",
        "GBPUSD": "🇬🇧🇺🇸",
        "USDJPY": "🇺🇸🇯🇵",
        "USDCHF": "🇺🇸🇨🇭",
        "USDCAD": "🇺🇸🇨🇦",
        "AUDUSD": "🇦🇺🇺🇸",
        "NZDUSD": "🇳🇿🇺🇸",
        "EURGBP": "🇪🇺🇬🇧",
        "EURJPY": "🇪🇺🇯🇵",
        "GBPJPY": "🇬🇧🇯🇵",
        "GBPCHF": "🇬🇧🇨🇭",
        "EURCHF": "🇪🇺🇨🇭",
        "AUDJPY": "🇦🇺🇯🇵",
        "CADJPY": "🇨🇦🇯🇵",
        "CHFJPY": "🇨🇭🇯🇵",
        "AUDCAD": "🇦🇺🇨🇦",
        "AUDNZD": "🇦🇺🇳🇿",
        "NZDJPY": "🇳🇿🇯🇵",
        "EURAUD": "🇪🇺🇦🇺",
        "EURNZD": "🇪🇺🇳🇿",
        "GBPAUD": "🇬🇧🇦🇺",
        "GBPCAD": "🇬🇧🇨🇦",
        "GBPNZD": "🇬🇧🇳🇿",
        "AUDCHF": "🇦🇺🇨🇭",
        "CADCHF": "🇨🇦🇨🇭",
        "NZDCHF": "🇳🇿🇨🇭",
    }

    return flags.get(asset, "📊")


def normalize_symbol(symbol: str) -> str:

    if not symbol:
        return ""

    return (
        symbol.upper()
        .replace("/", "")
        .replace("-", "")
        .replace("_", "")
        .strip()
    )


def is_gold(symbol: str) -> bool:

    symbol = normalize_symbol(symbol)

    return (
        symbol == "XAUUSD"
        or "GOLD" in symbol
    )


def get_pip_size(symbol: str) -> float:

    symbol = normalize_symbol(symbol)

    if is_gold(symbol):
        return 0.01

    if symbol.endswith("JPY"):
        return 0.01

    return 0.0001


def get_decimal_places(symbol: str) -> int:

    symbol = normalize_symbol(symbol)

    if is_gold(symbol):
        return 2

    if symbol.endswith("JPY"):
        return 3

    return 5


def calculate_forex_lot_size(
    symbol: str,
    entry_price: float,
    stop_loss_price: float,
    risk_amount: float
):

    symbol = normalize_symbol(symbol)

    if entry_price <= 0 or stop_loss_price <= 0:
        return 0.0

    distance = abs(
        entry_price - stop_loss_price
    )

    if distance <= 0:
        return 0.0

    # --------------------------------------------------------------------------
    # XAUUSD
    # --------------------------------------------------------------------------

    if is_gold(symbol):

        # Approximate USD P/L:
        # price movement × ounces
        raw_lot = (
            risk_amount
            / (distance * GOLD_CONTRACT_SIZE)
        )

    # --------------------------------------------------------------------------
    # USD-QUOTED PAIRS
    # EURUSD / GBPUSD / AUDUSD / NZDUSD
    # --------------------------------------------------------------------------

    elif symbol.endswith("USD"):

        # 1 pip at 1 standard lot ≈ $10
        pip_size = get_pip_size(symbol)

        pip_distance = (
            distance / pip_size
        )

        pip_value_per_lot = 10.0

        if pip_distance <= 0:
            return 0.0

        raw_lot = (
            risk_amount
            / (pip_distance * pip_value_per_lot)
        )

    # --------------------------------------------------------------------------
    # JPY PAIRS / CROSS PAIRS
    #
    # Exact pip value depends on live exchange rates.
    # We use an approximate risk model here.
    # The user should verify the final lot size in MT5.
    # --------------------------------------------------------------------------

    else:

        pip_size = get_pip_size(symbol)

        pip_distance = (
            distance / pip_size
        )

        # Conservative approximate pip value
        # for cross/JPY pairs.
        approximate_pip_value = 8.0

        if pip_distance <= 0:
            return 0.0

        raw_lot = (
            risk_amount
            / (
                pip_distance
                * approximate_pip_value
            )
        )

    # --------------------------------------------------------------------------
    # Practical rounding DOWN
    # --------------------------------------------------------------------------

    if raw_lot <= 0:
        return 0.0

    # Round down to 0.01 lot.
    lot = math.floor(
        raw_lot * 100
    ) / 100

    # Never allow zero if a valid calculation exists.
    if lot < 0.01:
        lot = 0.01

    return round(lot, 2)


def calculate_actual_risk(
    symbol: str,
    entry_price: float,
    stop_loss_price: float,
    lot_size: float
):

    symbol = normalize_symbol(symbol)

    distance = abs(
        entry_price - stop_loss_price
    )

    if distance <= 0 or lot_size <= 0:
        return 0.0

    if is_gold(symbol):

        return (
            distance
            * GOLD_CONTRACT_SIZE
            * lot_size
        )

    if symbol.endswith("USD"):

        pip_size = get_pip_size(symbol)

        pip_distance = (
            distance / pip_size
        )

        return (
            pip_distance
            * 10.0
            * lot_size
        )

    pip_size = get_pip_size(symbol)

    pip_distance = (
        distance / pip_size
    )

    return (
        pip_distance
        * 8.0
        * lot_size
    )


def parse_json_response(
    raw_content: str
) -> dict:

    content = raw_content.strip()

    if "```json" in content:

        content = (
            content
            .split("```json")[1]
            .split("```")[0]
            .strip()
        )

    elif "```" in content:

        content = (
            content
            .split("```")[1]
            .split("```")[0]
            .strip()
        )

    if "{" in content and "}" in content:

        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1

        content = content[
            start_idx:end_idx
        ]

    return json.loads(content)


# ==============================================================================
# OPENROUTER AI FALLBACK
# ==============================================================================

def execute_with_fallbacks(
    api_key: str,
    messages: list,
    max_tokens: int = 750
):

    cleaned_key = (
        api_key.strip()
        if api_key
        else ""
    )

    if not cleaned_key:

        raise Exception(
            "OpenRouter Secret Key is missing. "
            "Enter your key in the sidebar."
        )

    fallback_models = [
        "openai/gpt-4o",
        "deepseek/deepseek-chat",
        "google/gemini-2.5-flash",
    ]

    last_error = ""

    for model_id in fallback_models:

        try:

            response = requests.post(

                "https://openrouter.ai/api/v1/chat/completions",

                headers={
                    "Authorization":
                        f"Bearer {cleaned_key}",

                    "HTTP-Referer":
                        "https://streamlit.app",

                    "X-OpenRouter-Title":
                        "Shawkat Prop Firm AI Challenge",
                },

                json={
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },

                timeout=45,
            )

            if response.status_code == 200:

                res_json = response.json()

                if (
                    "choices" in res_json
                    and len(res_json["choices"]) > 0
                ):

                    raw_text = (
                        res_json["choices"][0]
                        ["message"]
                        ["content"]
                    )

                    return parse_json_response(
                        raw_text
                    )

                last_error = (
                    f"{model_id}: Empty response"
                )

            else:

                last_error = (
                    f"{model_id}: "
                    f"HTTP {response.status_code}: "
                    f"{response.text}"
                )

        except Exception as e:

            last_error = (
                f"{model_id}: {str(e)}"
            )

    raise Exception(
        "All AI models failed.\n\n"
        + last_error
    )


# ==============================================================================
# AI VISION ANALYZER
# ==============================================================================

def generate_prop_vision_signal(
    api_key: str,
    image_bytes: bytes,
    account_balance: float
):

    base64_image = (
        base64.b64encode(
            image_bytes
        ).decode("utf-8")
    )

    local_tz = pytz.timezone(
        "Asia/Karachi"
    )

    now_local = datetime.now(
        local_tz
    )

    current_local_time = (
        now_local.strftime(
            "%H:%M:%S"
        )
    )

    risk_amount = (
        account_balance
        * RISK_PERCENT
        / 100.0
    )

    phase = (
        st.session_state.phase
    )

    if phase == "Phase 1":

        target = PHASE_1_TARGET

    else:

        target = PHASE_2_TARGET

    pairs_text = ", ".join(
        SUPPORTED_PAIRS
    )

    prompt = f"""
You are an advanced institutional-style
technical analyst and prop-firm risk manager.

CURRENT TIME:
{current_local_time} PKT

==================================================
FUNDINGPIPS $5K PRACTICE CONFIGURATION
==================================================

Starting account:
$5,000

Current balance:
${account_balance:,.2f}

Current phase:
{phase}

Current phase profit target:
${target:,.2f}

Maximum daily loss:
$250

Maximum total loss:
$500

STRICT RISK PER TRADE:
0.5%

Maximum intended risk:
${risk_amount:,.2f}

DEFAULT RISK/REWARD:
1:2

MAX TRADES PER DAY:
3

==================================================
SUPPORTED MARKETS
==================================================

{pairs_text}

The uploaded screenshot may show ANY of
the supported forex pairs or XAUUSD.

Identify the actual symbol shown in the
chart.

Do NOT assume the chart is XAUUSD.

==================================================
ANALYSIS
==================================================

Analyze:

- Market structure
- Trend
- Higher highs / lower lows
- Support and resistance
- Liquidity
- Liquidity sweeps
- Break of structure
- Change of character
- Order blocks
- Fair value gaps
- Momentum
- Candlestick structure
- Rejection
- Nearby highs and lows
- Potential stop-hunt areas
- Entry quality
- Risk/reward quality

==================================================
TRADE DECISION
==================================================

If there is NOT a sufficiently clear setup:

signal MUST be:

"NO TRADE"

Do NOT force a BUY or SELL.

If a valid setup exists:

1. Identify BUY or SELL.

2. Determine a logical entry.

3. Determine a structural Stop Loss.

4. Determine Take Profit at approximately
   1:2 risk/reward.

5. Calculate the suggested lot size.

6. Maximum intended risk must be
   approximately ${risk_amount:,.2f}
   or LOWER.

7. Never increase lot size simply to
   reach the profit target faster.

8. Maximum recommended trades per day
   is 3.

9. Prefer high-quality setups over
   frequent trades.

==================================================
LOT SIZE CALCULATION
==================================================

For standard forex:

1 standard lot = 100,000 units.

For XAUUSD:

1 standard lot = 100 oz.

Calculate the lot size based on:

- Symbol
- Entry
- Stop Loss
- Maximum risk

For USD-quoted major pairs such as
EURUSD / GBPUSD / AUDUSD / NZDUSD,
pip value is approximately $10 per pip
per 1.00 standard lot.

For JPY and cross pairs, pip value
depends on the relevant exchange rate.

Be conservative.

The final lot size should NEVER intentionally
risk more than the allowed risk.

==================================================
TIMING
==================================================

Do NOT pretend that future timing is certain.

If useful, provide an approximate
entry/TP timing estimate.

Never guarantee that TP will hit.

==================================================
IMPORTANT
==================================================

This is a risk-management and analysis tool.

Do not claim guaranteed accuracy.

Do not guarantee profit.

Do not fabricate market data that is not
visible in the screenshot.

Do not invent an exact price if the chart
does not provide enough information.

==================================================
JSON OUTPUT
==================================================

Return ONLY valid JSON.

Required keys:

"asset"
"live_price"
"signal"
"entry_price"
"stop_loss_price"
"take_profit_price"
"risk_reward_ratio"
"recommended_risk_amount"
"suggested_lot_size"
"estimated_pip_distance"
"estimated_dollar_risk"
"accuracy"
"setup_score"
"reason"
"estimated_entry_time"
"estimated_tp_time"

signal must be exactly one of:

"BUY"

"SELL"

"NO TRADE"
"""

    messages = [

        {
            "role": "user",

            "content": [

                {
                    "type": "text",
                    "text": prompt
                },

                {
                    "type": "image_url",

                    "image_url": {

                        "url":
                            "data:image/jpeg;base64,"
                            + base64_image

                    },
                },

            ],
        }

    ]

    return execute_with_fallbacks(
        api_key,
        messages,
        max_tokens=750
    )


# ==============================================================================
# SIDEBAR
# ==============================================================================

st.sidebar.title(
    "🛡️ Shawkat Prop Firm AI"
)

st.session_state.api_key = (
    st.sidebar.text_input(
        "OpenRouter Secret Key",
        value=st.session_state.api_key,
        type="password",
        help="Your OpenRouter API key."
    )
)

st.sidebar.markdown("---")

st.sidebar.subheader(
    "⚙️ $5K Challenge"
)

selected_phase = st.sidebar.selectbox(
    "Challenge Phase",
    [
        "Phase 1",
        "Phase 2"
    ]
)

st.sidebar.markdown(
    """
### 💰 Account

**Starting Balance:** $5,000

### 🎯 Targets

**Phase 1:** +$400 / 8%

**Phase 2:** +$250 / 5%

### 🛡️ Risk

**Per Trade:** 0.5%

**Approx. Risk:** $25

**Daily Loss:** $250

**Maximum Loss:** $500

### 📊 Trading

**Max Trades/Day:** 3

**Default R:R:** 1:2
"""
)

st.sidebar.markdown("---")

if st.sidebar.button(
    "🚀 Initialize / Reset $5K",
    type="primary"
):

    st.session_state.initial_balance = (
        ACCOUNT_SIZE
    )

    st.session_state.current_balance = (
        ACCOUNT_SIZE
    )

    st.session_state.phase = (
        selected_phase
    )

    st.session_state.risk_per_trade = (
        RISK_PERCENT
    )

    if selected_phase == "Phase 1":

        st.session_state.profit_target = (
            PHASE_1_TARGET
        )

    else:

        st.session_state.profit_target = (
            PHASE_2_TARGET
        )

    st.session_state.max_daily_loss = (
        DAILY_LOSS_LIMIT
    )

    st.session_state.max_total_loss = (
        MAX_TOTAL_LOSS
    )

    st.session_state.max_trades_per_day = (
        MAX_TRADES_PER_DAY
    )

    st.session_state.current_pnl = 0.0
    st.session_state.daily_pnl = 0.0

    st.session_state.trades_won = 0
    st.session_state.trades_lost = 0
    st.session_state.trades_today = 0

    st.session_state.last_signal = None

    st.session_state.prop_active = True

    st.sidebar.success(
        f"{selected_phase} initialized!"
    )


# ==============================================================================
# ACTIVE ACCOUNT SIDEBAR
# ==============================================================================

if st.session_state.prop_active:

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "📊 Account Status"
    )

    st.sidebar.metric(
        "Balance",
        f"${st.session_state.current_balance:,.2f}"
    )

    st.sidebar.metric(
        "Total P/L",
        f"${st.session_state.current_pnl:,.2f}"
    )

    st.sidebar.metric(
        "Daily P/L",
        f"${st.session_state.daily_pnl:,.2f}"
    )

    st.sidebar.metric(
        "Trades Today",
        f"{st.session_state.trades_today}/3"
    )

    st.sidebar.markdown(
        f"""
**Phase:** {st.session_state.phase}

**Risk:** 0.5%

**Max Risk/Trade:**
${st.session_state.current_balance * 0.005:,.2f}

**Target:**
${st.session_state.profit_target:,.2f}

**Daily Loss Limit:**
${st.session_state.max_daily_loss:,.2f}

**Max Loss:**
${st.session_state.max_total_loss:,.2f}
"""
    )


# ==============================================================================
# MAIN APP
# ==============================================================================

st.title(
    "🛡️ Shawkat Prop Firm AI Challenge Manager"
)

st.caption(
    "$5K FundingPips 2-Step Trial • "
    "Forex + XAUUSD • 0.5% Risk • 1:2 R:R"
)

current_api_key = (
    st.session_state.api_key
)

if (
    not current_api_key
    or not current_api_key.strip()
):

    st.warning(
        "⚠️ Enter your OpenRouter Secret Key "
        "in the sidebar."
    )

    st.stop()


if not st.session_state.prop_active:

    st.info(
        "👈 Select Phase 1 or Phase 2 "
        "and initialize the $5K challenge."
    )

    st.stop()


# ==============================================================================
# SAFETY LOCKS
# ==============================================================================

if (
    st.session_state.current_pnl
    >= st.session_state.profit_target
):

    st.success(
        f"""
🎉 **{st.session_state.phase}
PROFIT TARGET ACHIEVED!**

Target:
${st.session_state.profit_target:,.2f}

Current P/L:
${st.session_state.current_pnl:,.2f}
"""
    )

    st.stop()


if (
    st.session_state.daily_pnl
    <= -st.session_state.max_daily_loss
):

    st.error(
        f"""
🛑 **DAILY LOSS LIMIT HIT**

Daily loss:
${abs(st.session_state.daily_pnl):,.2f}

Limit:
${st.session_state.max_daily_loss:,.2f}

New trading signals are locked.
"""
    )

    st.stop()


if (
    st.session_state.current_pnl
    <= -st.session_state.max_total_loss
):

    st.error(
        f"""
🚨 **MAXIMUM LOSS LIMIT HIT**

Total loss:
${abs(st.session_state.current_pnl):,.2f}

Maximum allowed:
${st.session_state.max_total_loss:,.2f}

Challenge failed.
"""
    )

    st.stop()


# ==============================================================================
# DASHBOARD
# ==============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "💰 Balance",
        f"${st.session_state.current_balance:,.2f}"
    )

with col2:

    st.metric(
        "🎯 Target",
        f"${st.session_state.profit_target:,.2f}"
    )

with col3:

    st.metric(
        "🛡️ Risk/Trade",
        f"${st.session_state.current_balance * 0.005:,.2f}"
    )

with col4:

    st.metric(
        "📊 Trades Today",
        f"{st.session_state.trades_today}/3"
    )


st.markdown("---")


# ==============================================================================
# TABS
# ==============================================================================

tab1, tab2 = st.tabs(
    [
        "1️⃣ AI Chart Analyzer",
        "2️⃣ Log Trade"
    ]
)


# ==============================================================================
# TAB 1 — AI CHART ANALYZER
# ==============================================================================

with tab1:

    st.subheader(
        "🧠 Multi-Market AI Chart Analyzer"
    )

    st.markdown(
        """
Upload a chart for any supported forex pair
or XAUUSD.

The AI identifies the symbol from the chart
and calculates risk based on the actual
Entry and Stop Loss.
"""
    )

    st.markdown(
        f"""
**Account:** $5,000

**Current Balance:**
${st.session_state.current_balance:,.2f}

**Risk:** 0.5%

**Maximum Risk:**
${st.session_state.current_balance * 0.005:,.2f}

**R:R:** 1:2
"""
    )

    st.markdown("---")

    st.markdown(
        "**Supported:** "
        + ", ".join(SUPPORTED_PAIRS)
    )

    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Upload TradingView / MT5 Chart",
        type=[
            "jpg",
            "jpeg",
            "png"
        ]
    )

    if uploaded_file is not None:

        image = Image.open(
            uploaded_file
        )

        st.image(
            image,
            caption="Uploaded Market Chart",
            use_container_width=True
        )

        if (
            st.session_state.trades_today
            >= st.session_state.max_trades_per_day
        ):

            st.error(
                "🛑 You have reached the "
                "3-trade daily limit."
            )

        else:

            if st.button(
                "🔍 Analyze Chart & Calculate Lot",
                type="primary",
                use_container_width=True
            ):

                with st.spinner(
                    "AI is analyzing market structure "
                    "and calculating risk..."
                ):

                    try:

                        img_bytes = (
                            uploaded_file.getvalue()
                        )

                        sig = (
                            generate_prop_vision_signal(
                                current_api_key,
                                img_bytes,
                                st.session_state.current_balance
                            )
                        )

                        # ------------------------------------------------------
                        # Normalize AI symbol
                        # ------------------------------------------------------

                        symbol = normalize_symbol(
                            sig.get(
                                "asset",
                                ""
                            )
                        )

                        if symbol:

                            sig["asset"] = symbol

                        # ------------------------------------------------------
                        # Recalculate risk/lot locally
                        # ------------------------------------------------------

                        try:

                            entry = float(
                                sig.get(
                                    "entry_price",
                                    0
                                )
                            )

                            sl = float(
                                sig.get(
                                    "stop_loss_price",
                                    0
                                )
                            )

                            if (
                                entry > 0
                                and sl > 0
                                and symbol
                                and sig.get("signal")
                                != "NO TRADE"
                            ):

                                max_risk = (
                                    st.session_state.current_balance
                                    * RISK_PERCENT
                                    / 100.0
                                )

                                lot = (
                                    calculate_forex_lot_size(
                                        symbol,
                                        entry,
                                        sl,
                                        max_risk
                                    )
                                )

                                actual_risk = (
                                    calculate_actual_risk(
                                        symbol,
                                        entry,
                                        sl,
                                        lot
                                    )
                                )

                                pip_size = (
                                    get_pip_size(
                                        symbol
                                    )
                                )

                                pip_distance = (
                                    abs(
                                        entry - sl
                                    )
                                    / pip_size
                                )

                                sig[
                                    "suggested_lot_size"
                                ] = lot

                                sig[
                                    "estimated_dollar_risk"
                                ] = round(
                                    actual_risk,
                                    2
                                )

                                sig[
                                    "estimated_pip_distance"
                                ] = round(
                                    pip_distance,
                                    1
                                )

                                sig[
                                    "recommended_risk_amount"
                                ] = round(
                                    max_risk,
                                    2
                                )

                        except Exception:
                            pass

                        st.session_state.last_signal = (
                            sig
                        )

                    except Exception as e:

                        st.error(
                            f"AI Error: {str(e)}"
                        )


# ==============================================================================
# TAB 2 — LOG TRADE
# ==============================================================================

with tab2:

    st.subheader(
        "📝 Log Completed Trade"
    )

    st.info(
        "Enter the actual profit or loss from "
        "your practice account after the trade closes."
    )

    current_balance = (
        st.session_state.current_balance
    )

    col1, col2 = st.columns(2)


    # --------------------------------------------------------------------------
    # WIN
    # --------------------------------------------------------------------------

    with col1:

        st.markdown(
            "### ✅ Winning Trade"
        )

        win_amount = st.number_input(
            "Profit ($)",
            min_value=0.01,
            max_value=10000.0,
            value=50.0,
            step=1.0,
            key="win_amount"
        )

        if st.button(
            "Save Winning Trade",
            type="primary",
            use_container_width=True
        ):

            if (
                st.session_state.trades_today
                >= MAX_TRADES_PER_DAY
            ):

                st.error(
                    "Daily trade limit reached."
                )

            else:

                new_balance = (
                    current_balance
                    + win_amount
                )

                st.session_state.current_balance = (
                    new_balance
                )

                st.session_state.current_pnl += (
                    win_amount
                )

                st.session_state.daily_pnl += (
                    win_amount
                )

                st.session_state.trades_won += 1

                st.session_state.trades_today += 1

                st.success(
                    f"Win saved! "
                    f"New balance: "
                    f"${new_balance:,.2f}"
                )

                st.rerun()


    # --------------------------------------------------------------------------
    # LOSS
    # --------------------------------------------------------------------------

    with col2:

        st.markdown(
            "### ❌ Losing Trade"
        )

        loss_amount = st.number_input(
            "Loss ($)",
            min_value=0.01,
            max_value=10000.0,
            value=25.0,
            step=1.0,
            key="loss_amount"
        )

        if st.button(
            "Save Losing Trade",
            type="secondary",
            use_container_width=True
        ):

            if (
                st.session_state.trades_today
                >= MAX_TRADES_PER_DAY
            ):

                st.error(
                    "Daily trade limit reached."
                )

            else:

                new_balance = (
                    current_balance
                    - loss_amount
                )

                st.session_state.current_balance = (
                    new_balance
                )

                st.session_state.current_pnl -= (
                    loss_amount
                )

                st.session_state.daily_pnl -= (
                    loss_amount
                )

                st.session_state.trades_lost += 1

                st.session_state.trades_today += 1

                st.warning(
                    f"Loss saved. "
                    f"New balance: "
                    f"${new_balance:,.2f}"
                )

                st.rerun()


    st.markdown("---")

    st.metric(
        "Current Balance",
        f"${st.session_state.current_balance:,.2f}"
    )

    st.metric(
        "Today's P/L",
        f"${st.session_state.daily_pnl:,.2f}"
    )


# ==============================================================================
# SIGNAL OUTPUT
# ==============================================================================

if st.session_state.last_signal:

    st.markdown("---")

    sig_data = (
        st.session_state.last_signal
    )

    asset = normalize_symbol(
        sig_data.get(
            "asset",
            ""
        )
    )

    if not asset:
        asset = "UNKNOWN"

    asset_flag = get_pair_flag(
        asset
    )

    signal_dir = (
        str(
            sig_data.get(
                "signal",
                "NO TRADE"
            )
        )
        .upper()
    )


    # --------------------------------------------------------------------------
    # NO TRADE
    # --------------------------------------------------------------------------

    if signal_dir == "NO TRADE":

        st.warning(
            "🟡 **NO TRADE**"
        )

        st.markdown(
            "### 🧠 AI Reason"
        )

        st.info(
            sig_data.get(
                "reason",
                "No sufficiently high-quality setup."
            )
        )


    # --------------------------------------------------------------------------
    # BUY / SELL
    # --------------------------------------------------------------------------

    else:

        if signal_dir == "BUY":

            signal_icon = "🟢 BUY"

        else:

            signal_icon = "🔴 SELL"


        st.markdown(
            f"## {asset_flag} "
            f"**{asset}**"
        )

        st.markdown(
            f"### Direction: **{signal_icon}**"
        )


        res_col1, res_col2 = (
            st.columns(2)
        )


        # ----------------------------------------------------------------------
        # LEVELS
        # ----------------------------------------------------------------------

        with res_col1:

            st.write(
                "**Entry:** "
                f"`{sig_data.get('entry_price', 'N/A')}`"
            )

            st.write(
                "**Stop Loss:** 🛡️ "
                f"`{sig_data.get('stop_loss_price', 'N/A')}`"
            )

            st.write(
                "**Take Profit:** 🎯 "
                f"`{sig_data.get('take_profit_price', 'N/A')}`"
            )

            st.write(
                "**R:R:** "
                f"`{sig_data.get('risk_reward_ratio', '1:2')}`"
            )

            st.write(
                "**SL Distance:** "
                f"`{sig_data.get('estimated_pip_distance', 'N/A')} pips`"
            )


        # ----------------------------------------------------------------------
        # RISK
        # ----------------------------------------------------------------------

        with res_col2:

            st.write(
                "**Maximum Planned Risk:** "
                f"`${sig_data.get('recommended_risk_amount', 'N/A')}`"
            )

            st.write(
                "**Suggested Lot:** 📦 "
                f"`{sig_data.get('suggested_lot_size', 'N/A')}`"
            )

            st.write(
                "**Estimated Dollar Risk:** "
                f"`${sig_data.get('estimated_dollar_risk', 'N/A')}`"
            )

            st.write(
                "**Setup Score:** ⭐ "
                f"`{sig_data.get('setup_score', 'N/A')}/10`"
            )

            st.write(
                "**AI Accuracy Estimate:** "
                f"`{sig_data.get('accuracy', 'N/A')}`"
            )


        st.markdown("---")


        # ----------------------------------------------------------------------
        # TIMING
        # ----------------------------------------------------------------------

        st.markdown(
            "### ⏰ Timing Estimate"
        )

        timing_col1, timing_col2 = (
            st.columns(2)
        )

        with timing_col1:

            st.write(
                "**Possible Entry:** "
                f"`{sig_data.get('estimated_entry_time', 'N/A')}`"
            )

        with timing_col2:

            st.write(
                "**Possible TP:** "
                f"`{sig_data.get('estimated_tp_time', 'N/A')}`"
            )


        st.markdown("---")


        # ----------------------------------------------------------------------
        # THESIS
        # ----------------------------------------------------------------------

        st.markdown(
            "### 🧠 Institutional Trade Thesis"
        )

        st.info(
            sig_data.get(
                "reason",
                "No detailed reason provided."
            )
        )


        st.markdown("---")


        # ----------------------------------------------------------------------
        # RISK WARNING
        # ----------------------------------------------------------------------

        st.warning(
            f"""
⚠️ **PROP RISK CHECK**

Account:
${st.session_state.current_balance:,.2f}

Maximum intended risk:
${st.session_state.current_balance * 0.005:,.2f}

Daily loss limit:
$250

Maximum total loss:
$500

Daily trades:
{st.session_state.trades_today}/3

Verify the symbol, entry, SL, TP and lot
size in MT5 before placing any order.

AI analysis is not a guarantee of profit.
"""
        )


# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("---")

st.caption(
    "Shawkat Prop Firm AI Challenge Manager • "
    "$5K 2-Step Practice Configuration • "
    "Forex + XAUUSD • 0.5% Risk • 1:2 R:R"
)
