"""Investco leveraged-position calculator for Streamlit."""

from __future__ import annotations

from math import ceil

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
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    [data-testid="stAppDeployButton"], [data-testid="stMainMenu"] { display: none; }
    .block-container { max-width: 1120px; padding-top: 2.5rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { border-right: 1px solid #e0e6f0; }
    [data-testid="stSidebar"] .block-container { padding-top: 2rem; }
    [data-testid="stMain"] h1 { letter-spacing: -0.035em; }
    [data-testid="stMain"] h3 { letter-spacing: -0.015em; }
    [data-testid="stMetric"] {
        background: #f7f9fd;
        padding: 1.15rem;
        border: 1px solid #e0e6f0;
        border-radius: 0.8rem;
        height: 100%;
    }
    [data-testid="stMetricLabel"] { opacity: 0.85; }
    [data-testid="stMetricValue"] { font-size: clamp(1.25rem, 2vw, 1.75rem); }
    [data-testid="stMetricValue"] > div {
        white-space: normal;
        overflow-wrap: anywhere;
    }
    [data-testid="stTabs"] [role="tablist"] { gap: 1.5rem; border-bottom: 1px solid #e0e6f0; }
    [data-testid="stTabs"] [role="tab"] {
        min-height: 3rem;
        padding: 0.75rem 0.2rem;
        font-weight: 600;
    }
    [data-testid="stMain"] [data-testid="stExpander"] {
        border-color: #e0e6f0;
        border-radius: 0.75rem;
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
        .block-container { padding: 1.25rem 1rem 2rem; }
        [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex-basis: 100%;
        }
        [data-testid="stMetric"] { padding: 0.9rem 1rem; }
        [data-testid="stTabs"] [role="tablist"] { gap: 1rem; }
        [data-testid="stTabs"] [role="tab"] { flex: 1 1 auto; }
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


with st.sidebar:
    st.title("Investco")
    st.caption("TRADE CALCULATOR")
    st.divider()
    st.subheader("Your trade")
    side_label = st.radio("Buy or sell", ("BUY · Long", "SELL · Short"), horizontal=True)
    side = "buy" if side_label.startswith("BUY") else "sell"
    asset = st.text_input("Asset name (optional)", placeholder="e.g. Bitcoin")
    quote_currency = st.selectbox("Price currency", CURRENCIES, index=1)
    entry_price = st.number_input(
        f"Buy or sell price ({quote_currency})", min_value=1, value=3500, step=1
    )
    target_price = st.number_input(
        f"Target price ({quote_currency})", min_value=1, value=5000, step=1
    )
    investment_currency = st.selectbox("Your money's currency", CURRENCIES, index=0)
    investment = st.number_input(
        f"Money for this trade ({investment_currency})", min_value=1, value=35000, step=100
    )
    leverage = st.slider("Leverage", min_value=1, max_value=100, value=5, step=1, format="%d×")

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
            "Minimum margin rate (%)", min_value=0.0, max_value=100.0, value=0.5, step=0.1,
            help="The exchange's maintenance margin rate. Decimal values are allowed.",
        )
        opening_fee_rate = st.number_input(
            "Opening fee (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.01
        )
        closing_fee_rate = st.number_input(
            "Closing fee (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.01
        )
        funding_fee = st.number_input(
            f"One-time funding fee ({investment_currency})", min_value=0, value=0, step=1
        )

st.title("Trade calculator")
st.caption("See your possible profit or loss and plan for liquidation.")
st.caption("Edit your trade details in the sidebar. On a phone, open it using the top-left arrow.")

errors: list[str] = []
if maintenance_rate >= 100:
    errors.append("Maintenance margin must be less than 100%.")
if opening_fee_rate >= 100:
    errors.append("Opening fee must be less than 100%.")
if closing_fee_rate >= 100:
    errors.append("Closing fee must be less than 100%.")
if exchange_rate_error:
    errors.append(exchange_rate_error)

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

if errors:
    for error in errors:
        st.error(error)
elif position is not None:
    st.caption(
        f"{asset.strip() or 'Your position'} · {side_label} · "
        f"{money(position.position_notional, investment_currency)} trade value"
    )
    overview_tab, protection_tab = st.tabs(["Trade summary", "Save Liquidation"])

    with overview_tab:
        st.subheader("If your target is reached")
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
                    {"Metric": "Entry price", "Value": price(position.entry_price, quote_currency)},
                    {"Metric": "Target price", "Value": price(position.target_price, quote_currency)},
                    {"Metric": "Price movement", "Value": f"{signed_money(position.price_change, quote_currency)} ({percent(position.price_change_percent, signed=True)})"},
                    {"Metric": "Gross profit / loss", "Value": signed_money(position.gross_profit_loss, investment_currency)},
                    {"Metric": "Fees and funding", "Value": money(position.total_fees, investment_currency)},
                ]
            )

        st.subheader("Liquidation price")
        liq_col, equity_col, buffer_col = st.columns(3)
        liq_col.metric("Estimated liquidation price", price(position.liquidation_price, quote_currency))
        equity_col.metric("Money after opening fees", money(position.available_equity, investment_currency))
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
        with deposit_col, st.container(border=True):
            st.markdown("#### I know how much to add")
            deposit_text = st.text_input(
                f"Money to add ({investment_currency})",
                placeholder="Enter an amount",
                key="deposit",
            )
            if deposit_text.strip():
                try:
                    deposit = float(deposit_text)
                except ValueError:
                    st.warning("Additional margin must be a number.")
                else:
                    try:
                        deposit_position = calculate_position_with_deposit(position, deposit)
                    except ValueError as error:
                        st.warning(str(error))
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
        with stress_col, st.container(border=True):
            st.markdown("#### I know the price to survive")
            stress_text = st.text_input(
                f"Price to survive ({quote_currency})",
                placeholder="Enter a price beyond liquidation",
                key="stress",
            )
            if stress_text.strip():
                try:
                    stress_price = float(stress_text)
                except ValueError:
                    st.warning("Stress price must be a number.")
                else:
                    try:
                        margin_result = calculate_additional_margin(position, stress_price)
                    except ValueError as error:
                        st.warning(str(error))
                    else:
                        if not margin_result.valid:
                            st.warning(margin_result.reason)
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
        "Results are rounded to whole numbers except asset quantity, which has five decimal places; "
        "required margin is rounded up. Small prices and quantities can round to zero, and liquidation and stress prices can "
        "appear equal after rounding. Calculations use full input precision."
    )
    st.caption(
        "Simplified isolated-margin estimates for planning only, not financial advice. "
        "Actual exchange rules, fees and liquidation levels may differ."
    )
