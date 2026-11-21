"""Investco leveraged-position calculator for Streamlit."""

from __future__ import annotations

from math import ceil, isfinite

import streamlit as st

from calculations import (
    calculate_additional_margin,
    calculate_position,
    calculate_position_with_deposit,
)

CURRENCIES = ("INR", "USD", "USDT", "EUR", "GBP")
CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "USDT": "₮", "EUR": "€", "GBP": "£"}

st.set_page_config(
    page_title="Investco | Trade calculator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
    [data-testid="stExpandSidebarButton"] { display: none; }
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: #f3f7f7;
    }
    [data-testid="stMain"], [data-testid="stMain"] h1,
    [data-testid="stMain"] h2, [data-testid="stMain"] h3,
    [data-testid="stMain"] h4, [data-testid="stMain"] p,
    [data-testid="stMain"] button, [data-testid="stMain"] input,
    [data-testid="stMain"] select, [data-testid="stMain"] [data-testid="stMetricValue"] {
        font-family: "Aptos", "Segoe UI", "Helvetica Neue", sans-serif;
    }
    .block-container { max-width: 1080px; padding-top: 2.5rem; padding-bottom: 3.5rem; }
    [data-testid="stMain"] h1 {
        color: #102c35;
        font-size: clamp(2.2rem, 4vw, 2.8rem);
        font-weight: 750;
        letter-spacing: -0.045em;
    }
    [data-testid="stMain"] h3, [data-testid="stMain"] h4 {
        color: #16343c;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    [data-testid="stMain"] h3 { font-size: 1.25rem; }
    [data-testid="stMain"] h4 { font-size: 1.05rem; }
    [data-testid="stMain"] [data-testid="stCaptionContainer"] {
        color: #536b72;
        line-height: 1.55;
        opacity: 1;
    }
    [data-testid="stMain"] [data-testid="stCaptionContainer"] p { font-size: 0.875rem; }
    [data-testid="stMain"] label p {
        color: #29444c;
        font-weight: 600;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        padding: 1.25rem;
        border: 1px solid #dce8e7;
        border-top: 3px solid #9ccdc5;
        border-radius: 0.75rem;
        box-shadow: 0 3px 14px rgba(20, 54, 60, 0.04);
        height: 100%;
    }
    [data-testid="stMetricLabel"] {
        color: #526a70;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #11363c;
        font-size: clamp(1.35rem, 2vw, 1.8rem);
        font-weight: 700;
        letter-spacing: -0.03em;
        font-variant-numeric: tabular-nums;
    }
    [data-testid="stMetricValue"] > div {
        white-space: normal;
        overflow-wrap: anywhere;
    }
    [data-testid="stTabs"] [role="tablist"] {
        gap: 1.5rem;
        border-bottom: 1px solid #cfdddc;
    }
    [data-testid="stTabs"] [role="tab"] {
        min-height: 3rem;
        padding: 0.75rem 0.2rem;
        font-weight: 600;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #08766c; }
    [data-testid="stMain"] [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #d9e5e4;
        border-radius: 0.85rem;
        box-shadow: 0 4px 18px rgba(20, 54, 60, 0.04);
    }
    [data-testid="stMain"] [data-testid="stExpander"] [data-testid="stExpander"] {
        background: #f8fbfa;
        box-shadow: none;
    }
    [data-testid="stMain"] [data-testid="stExpander"] summary p {
        color: #193a41;
        font-weight: 700;
    }
    [data-testid="stMain"] [data-testid="stNumberInputContainer"],
    [data-testid="stMain"] [data-testid="stTextInputRootElement"] {
        border-radius: 0.5rem;
    }
    [data-testid="stMain"] [data-testid="stButton"] button {
        min-height: 2.8rem;
        border-radius: 0.55rem;
        font-weight: 650;
    }
    [data-testid="stMain"] [data-testid="stButton"] button[kind="primary"] {
        background: #08766c;
        border-color: #08766c;
        color: #ffffff;
    }
    [data-testid="stMain"] [data-testid="stButton"] button[kind="primary"]:hover {
        background: #075e57;
        border-color: #075e57;
        color: #ffffff;
    }
    [data-testid="stMain"] [data-testid="stButton"] button[kind="secondary"] {
        color: #15574f;
        border-color: #adcac5;
        background: #ffffff;
    }
    [data-testid="stMain"] [data-testid="stButton"] button[kind="secondary"]:hover {
        color: #075e57;
        border-color: #08766c;
        background: #edf7f5;
    }
    [data-testid="stMain"] .st-key-deposit_card,
    [data-testid="stMain"] .st-key-stress_card {
        background: #ffffff;
        border-color: #d9e5e4;
        border-radius: 0.85rem;
        box-shadow: 0 4px 18px rgba(20, 54, 60, 0.04);
    }
    @media (max-width: 900px) {
        [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
        }
        [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 220px;
            width: auto;
            min-width: 0;
        }
    }
    @media (max-width: 600px) {
        .block-container { padding: 1.4rem 1rem 2rem; }
        [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex-basis: 100%;
        }
        [data-testid="stMetric"] { padding: 0.9rem 1rem; }
        [data-testid="stTabs"] [role="tablist"] { gap: 1rem; }
        [data-testid="stTabs"] [role="tab"] { flex: 1 1 auto; }
    }
    [data-testid="stMain"] .st-key-price_pair [data-testid="stHorizontalBlock"],
    [data-testid="stMain"] .st-key-investment_pair [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap;
        gap: 0.5rem;
    }
    [data-testid="stMain"] .st-key-price_pair [data-testid="stColumn"],
    [data-testid="stMain"] .st-key-investment_pair [data-testid="stColumn"] {
        flex-basis: auto;
        min-width: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    rounded = round(value)
    return f"{'-' if rounded < 0 else ''}{symbol}{abs(rounded):,}"


def signed_money(value: float, currency: str) -> str:
    rounded = round(value)
    sign = "+" if rounded > 0 else "−" if rounded < 0 else ""
    return f"{sign}{money(abs(rounded), currency)}"


def price(value: float | None, currency: str) -> str:
    return "Not available" if value is None else money(value, currency)


def percent(value: float, *, signed: bool = False) -> str:
    rounded = round(value)
    return f"{rounded:+d}%" if signed and rounded else f"{rounded}%"


def highlight_invalid(keys: set[str]) -> None:
    if keys:
        selectors = ", ".join(
            f'.st-key-{key} :is([data-baseweb="input"], '
            '[data-testid="stNumberInputContainer"], [data-testid="stTextInputRootElement"])'
            for key in sorted(keys)
        )
        st.markdown(
            f"<style>{selectors} {{ box-shadow: 0 0 0 2px #c93434; border-radius: 0.4rem; }}</style>",
            unsafe_allow_html=True,
        )


st.title("Investco")
st.caption("Calculate your trade and plan for liquidation.")

with st.container(key=f"trade_inputs_{st.session_state.get('results_version', 0)}").expander(
    "Your trade", expanded=not st.session_state.get("calculated_inputs")
):
    side_label = st.radio("Buy or sell", ("BUY · Long", "SELL · Short"), horizontal=True)
    side = "buy" if side_label.startswith("BUY") else "sell"
    asset = st.text_input("Asset name (optional)", placeholder="e.g. Bitcoin")
    prices_col, money_col = st.columns(2, gap="large")
    with prices_col:
        with st.container(key="price_pair"):
            quote_col, entry_col = st.columns([1.15, 1.85], gap="small", vertical_alignment="bottom")
            with quote_col:
                quote_currency = st.selectbox("Price currency", CURRENCIES, index=1, key="quote_currency")
            with entry_col:
                entry_price = st.number_input(
                    "Buy price" if side == "buy" else "Sell price",
                    value=3500, step=1, key="entry_price"
                )
        target_price = st.number_input(
            f"Target price ({quote_currency})", value=5000, step=1, key="target_price"
        )
        target_feedback = st.empty()
    with money_col:
        with st.container(key="investment_pair"):
            currency_col, investment_col = st.columns([1.15, 1.85], gap="small", vertical_alignment="bottom")
            with currency_col:
                investment_currency = st.selectbox("Your currency", CURRENCIES, index=0, key="investment_currency")
            with investment_col:
                investment = st.number_input(
                    "Money for this trade", value=35000, step=100, key="investment"
                )
        leverage_input = st.number_input(
            "Leverage", value=5.0, step=1.0, format="%g", key="leverage"
        )
        leverage = (
            int(leverage_input)
            if isfinite(leverage_input) and leverage_input.is_integer()
            else leverage_input
        )

    exchange_rate_error = ""
    if investment_currency == quote_currency:
        exchange_rate = 1.0
    else:
        default_fx = "83.5" if investment_currency == "INR" and quote_currency == "USD" else ""
        exchange_rate_text = st.text_input(
            f"Exchange rate: {investment_currency} per {quote_currency}",
            value=default_fx,
            key=f"fx-{investment_currency}-{quote_currency}",
            help="Enter the exchange rate manually. Decimal values are allowed.",
        )
        exchange_feedback = st.empty()
        exchange_rate = None
        if not exchange_rate_text.strip():
            exchange_rate_error = "Enter an exchange rate for the selected currencies."
        else:
            try:
                exchange_rate = float(exchange_rate_text)
            except ValueError:
                exchange_rate_error = "Exchange rate must be a positive number."

    with st.expander("Fees and extra settings"):
        maintenance_rate = st.number_input(
            "Minimum margin rate (%)", value=0.5, step=0.1,
            help="The exchange's maintenance margin rate. Decimal values are allowed.",
            key="maintenance_rate",
        )
        opening_fee_rate = st.number_input(
            "Opening fee (%)", value=0.0, step=0.01, key="opening_fee_rate"
        )
        closing_fee_rate = st.number_input(
            "Closing fee (%)", value=0.0, step=0.01, key="closing_fee_rate"
        )
        funding_fee = st.number_input(
            f"One-time funding fee ({investment_currency})", value=0, step=1, key="funding_fee"
        )

    trade_feedback = st.empty()
    calculate_clicked = st.button("Calculate trade", type="primary", use_container_width=True)

errors: list[str] = []
invalid_fields: set[str] = set()
for key, value, message in (
    ("entry_price", entry_price, "Entry price must be greater than zero."),
    ("target_price", target_price, "Target price must be greater than zero."),
    ("investment", investment, "Money for this trade must be greater than zero."),
    ("funding_fee", funding_fee, "Funding fee cannot be negative."),
):
    if value < 0 or (value == 0 and key != "funding_fee"):
        errors.append(message)
        invalid_fields.add(key)
if not isfinite(leverage_input) or not leverage_input.is_integer() or not 1 <= leverage_input <= 100:
    errors.append("Leverage must be a whole number between 1 and 100.")
    invalid_fields.add("leverage")
if side == "buy" and target_price <= entry_price:
    target_error = "For a BUY trade, the target price must be higher than the buy price."
    errors.append(target_error)
    target_feedback.error(target_error)
    invalid_fields.add("target_price")
if side == "sell" and target_price >= entry_price:
    target_error = "For a SELL trade, the target price must be lower than the sell price."
    errors.append(target_error)
    target_feedback.error(target_error)
    invalid_fields.add("target_price")
if not 0 <= maintenance_rate < 100:
    errors.append("Maintenance margin must be at least 0% and less than 100%.")
    invalid_fields.add("maintenance_rate")
if not 0 <= opening_fee_rate < 100:
    errors.append("Opening fee must be at least 0% and less than 100%.")
    invalid_fields.add("opening_fee_rate")
if not 0 <= closing_fee_rate < 100:
    errors.append("Closing fee must be at least 0% and less than 100%.")
    invalid_fields.add("closing_fee_rate")
if maintenance_rate < 100 and closing_fee_rate < 100 and maintenance_rate + closing_fee_rate >= 100:
    errors.append("Maintenance margin and closing fee rates must total less than 100%.")
    invalid_fields.update(("maintenance_rate", "closing_fee_rate"))
if exchange_rate is not None and (not isfinite(exchange_rate) or exchange_rate <= 0):
    exchange_rate_error = "Exchange rate must be a positive, finite number."
if exchange_rate_error:
    errors.append(exchange_rate_error)
    exchange_feedback.error(exchange_rate_error)
    invalid_fields.add(f"fx-{investment_currency}-{quote_currency}")

inputs = (
    side, asset, quote_currency, entry_price, target_price, investment_currency,
    investment, leverage, exchange_rate, exchange_rate_error, maintenance_rate,
    opening_fee_rate, closing_fee_rate, funding_fee,
)
if st.session_state.get("calculated_inputs") != inputs:
    st.session_state.pop("calculated_inputs", None)

position = None
if not errors and exchange_rate is not None:
    try:
        position = calculate_position(
            side=side,
            entry_price=entry_price,
            target_price=target_price,
            investment=investment,
            leverage=leverage,
            quote_to_investment_rate=exchange_rate,
            maintenance_margin_rate=maintenance_rate / 100,
            opening_fee_rate=opening_fee_rate / 100,
            closing_fee_rate=closing_fee_rate / 100,
            funding_fee=funding_fee,
        )
    except ValueError as error:
        errors.append(str(error))
        if "at or beyond liquidation" in str(error):
            invalid_fields.update(("leverage", "investment"))
            invalid_fields.update(
                key for key, value in (
                    ("funding_fee", funding_fee), ("maintenance_rate", maintenance_rate),
                    ("opening_fee_rate", opening_fee_rate), ("closing_fee_rate", closing_fee_rate),
                ) if value
            )
        else:
            invalid_fields.update(("entry_price", "target_price", "investment", "leverage"))
            if investment_currency != quote_currency:
                invalid_fields.add(f"fx-{investment_currency}-{quote_currency}")

general_errors = [
    error for error in errors
    if error != exchange_rate_error and error not in (
        "For a BUY trade, the target price must be higher than the buy price.",
        "For a SELL trade, the target price must be lower than the sell price.",
    )
]
if general_errors:
    trade_feedback.error("\n\n".join(general_errors))
highlight_invalid(invalid_fields)

if calculate_clicked and not errors and position is not None:
    st.session_state["calculated_inputs"] = inputs
    st.session_state["results_version"] = st.session_state.get("results_version", 0) + 1
    st.rerun()

if position is not None and st.session_state.get("calculated_inputs") == inputs:
    st.caption(
        f"{asset.strip() or 'Your position'} · {side_label} · "
        f"{money(position.position_notional, investment_currency)} trade value"
    )
    overview_tab, protection_tab = st.container(
        key=f"results_{st.session_state.get('results_version', 0)}"
    ).tabs(["Trade summary", "Save Liquidation"])

    with overview_tab:
        st.subheader("If your target is reached")
        if position.net_profit_loss <= 0:
            st.warning("Fees and funding make this target unprofitable, despite the favorable price move.")
        pnl_col, return_col, value_col = st.columns(3)
        pnl_col.metric("Net profit / loss", signed_money(position.net_profit_loss, investment_currency))
        return_col.metric("Return on your money", percent(position.return_percent, signed=True))
        value_col.metric("Your money at target", money(position.total_value_at_target, investment_currency))

        with st.expander("Trade details"):
            st.table(
                [
                    {"Metric": "Money for this trade", "Value": money(position.investment, investment_currency)},
                    {"Metric": "Trade value", "Value": money(position.position_notional, investment_currency)},
                    {"Metric": "Asset quantity", "Value": f"{position.quantity:,.5f} units"},
                    {"Metric": "Buy price" if side == "buy" else "Sell price", "Value": price(position.entry_price, quote_currency)},
                    {"Metric": "Target price", "Value": price(position.target_price, quote_currency)},
                    {"Metric": "Price movement", "Value": f"{signed_money(position.target_price - position.entry_price, quote_currency)} ({percent((position.target_price - position.entry_price) / position.entry_price * 100, signed=True)})"},
                    {"Metric": "Gross profit / loss", "Value": signed_money(position.gross_profit_loss, investment_currency)},
                    {"Metric": "Fees and funding", "Value": money(position.total_fees, investment_currency)},
                ]
            )

        st.subheader("Liquidation price")
        liq_col, equity_col, buffer_col = st.columns(3)
        liq_col.metric("Estimated liquidation price", price(position.liquidation_price, quote_currency))
        equity_col.metric("Money after opening fees and funding", money(position.available_equity, investment_currency))
        buffer_col.metric("Money above minimum margin", money(position.remaining_margin_buffer, investment_currency))
        st.caption("Liquidation is when the exchange may close your trade because its available margin is too low.")
        if position.liquidation_price is None:
            st.caption("No positive liquidation level is available in this model.")
        else:
            direction = "drop" if side == "buy" else "rise"
            st.caption(
                f"Liquidation is a {percent(position.liquidation_distance_percent)} "
                f"{direction} from your starting price."
            )

    with protection_tab:
        st.subheader("Add money to your trade")
        st.caption(
            f"Both options use your selected {leverage}× leverage and current trade size. "
            "Adding money lowers the effective leverage; it does not increase the trade size."
        )
        st.caption(
            "The two options are separate. Add money before liquidation; "
            "an already closed trade cannot be restored."
        )
        deposit_col, stress_col = st.columns(2, gap="large")
        with deposit_col, st.container(border=True, key="deposit_card"):
            st.markdown("#### I know how much to add")
            deposit_text = st.text_input(
                f"Money to add ({investment_currency})",
                placeholder="Enter an amount",
                key="deposit",
            )
            st.button("Calculate new liquidation", key="calculate_deposit", use_container_width=True)
            if deposit_text.strip():
                try:
                    deposit = float(deposit_text)
                except ValueError:
                    st.warning("Additional margin must be a number.")
                    highlight_invalid({"deposit"})
                else:
                    try:
                        deposit_position = calculate_position_with_deposit(position, deposit)
                    except ValueError as error:
                        st.warning(str(error))
                        highlight_invalid({"deposit"})
                    else:
                        st.metric(
                            "New liquidation price",
                            price(deposit_position.liquidation_price, quote_currency),
                        )
                        total_margin = investment + deposit_position.additional_margin
                        st.caption(
                            f"Total money: {money(total_margin, investment_currency)} · "
                            f"Effective leverage: {round(position.position_notional / total_margin):,}×"
                        )
                        if deposit_position.liquidation_price is None:
                            st.caption("No positive liquidation level is available in this model.")
        with stress_col, st.container(border=True, key="stress_card"):
            st.markdown("#### I know the price to survive")
            stress_text = st.text_input(
                f"Price to survive ({quote_currency})",
                placeholder="Enter a price beyond liquidation",
                key="stress",
            )
            st.button("Calculate money to add", key="calculate_stress", use_container_width=True)
            if stress_text.strip():
                try:
                    stress_price = float(stress_text)
                except ValueError:
                    st.warning("Stress price must be a number.")
                    highlight_invalid({"stress"})
                else:
                    try:
                        margin_result = calculate_additional_margin(position, stress_price)
                    except ValueError as error:
                        st.warning(str(error))
                        highlight_invalid({"stress"})
                    else:
                        if not margin_result.valid:
                            st.warning(margin_result.reason)
                            highlight_invalid({"stress"})
                        else:
                            required_margin = ceil(margin_result.additional_margin_required)
                            funded = calculate_position_with_deposit(position, required_margin)
                            total_margin = investment + funded.additional_margin
                            st.metric("Money to add", money(required_margin, investment_currency))
                            st.caption(
                                f"New liquidation price: {price(funded.liquidation_price, quote_currency)} · "
                                f"Total money: {money(total_margin, investment_currency)}"
                            )
                            st.caption(
                                f"Effective leverage: {round(position.position_notional / total_margin):,}×"
                            )

    st.divider()
    st.caption(
        "Results are rounded; asset quantity uses five decimals and required margin is rounded up. "
        "Small values may round to zero, and liquidation and stress prices may appear equal."
    )
    st.caption(
        "Simplified isolated-margin estimates for planning only, not financial advice. "
        "Actual exchange rules, fees and liquidation levels may differ."
    )
