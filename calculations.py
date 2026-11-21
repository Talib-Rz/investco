"""Position P&L and simplified liquidation calculations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

Side = Literal["buy", "sell"]
SURVIVAL_BUFFER_PRICE = 0.01


@dataclass(frozen=True)
class PositionResult:
    side: Side
    entry_price: float
    target_price: float
    investment: float
    leverage: float
    quote_to_investment_rate: float
    position_notional: float
    quantity: float
    price_change: float
    price_change_percent: float
    return_percent: float
    gross_profit_loss: float
    net_profit_loss: float
    total_value_at_target: float
    opening_fee: float
    closing_fee: float
    funding_fee: float
    total_fees: float
    maintenance_margin_rate: float
    opening_fee_rate: float
    closing_fee_rate: float
    additional_margin: float
    available_equity: float
    remaining_margin_buffer: float
    liquidation_price: float | None
    liquidation_distance: float | None
    liquidation_distance_percent: float | None


@dataclass(frozen=True)
class MarginResult:
    valid: bool
    reason: str = ""
    stress_price: float | None = None
    additional_margin_required: float = 0
    total_margin_after_deposit: float = 0
    effective_leverage: float = 0
    updated_position: PositionResult | None = None
    existing_equity_at_stress: float = 0
    required_equity_at_stress: float = 0


def _assert_finite_positive(value: float, label: str) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be a positive number.")


def _assert_rate(value: float, label: str) -> None:
    if not isfinite(value) or value < 0 or value >= 1:
        raise ValueError(f"{label} must be at least 0 and less than 1.")


def calculate_position(
    *,
    side: Side,
    entry_price: float,
    target_price: float,
    investment: float,
    leverage: float,
    quote_to_investment_rate: float = 1,
    maintenance_margin_rate: float = 0.005,
    opening_fee_rate: float = 0,
    closing_fee_rate: float = 0,
    funding_fee: float = 0,
    additional_margin: float = 0,
) -> PositionResult:
    """Calculate target P&L and estimated isolated liquidation for a position."""
    if side not in ("buy", "sell"):
        raise ValueError("Side must be buy or sell.")
    _assert_finite_positive(entry_price, "Entry price")
    _assert_finite_positive(target_price, "Target price")
    _assert_finite_positive(investment, "Investment")
    _assert_finite_positive(leverage, "Leverage")
    _assert_finite_positive(quote_to_investment_rate, "Exchange rate")
    _assert_rate(maintenance_margin_rate, "Maintenance margin rate")
    _assert_rate(opening_fee_rate, "Opening fee rate")
    _assert_rate(closing_fee_rate, "Closing fee rate")
    if not isfinite(funding_fee) or funding_fee < 0:
        raise ValueError("Funding fee must be zero or a positive number.")
    if not isfinite(additional_margin) or additional_margin < 0:
        raise ValueError("Additional margin must be zero or a positive number.")

    position_notional = investment * leverage
    quantity = position_notional / (entry_price * quote_to_investment_rate)
    price_change = target_price - entry_price if side == "buy" else entry_price - target_price
    price_change_percent = price_change / entry_price * 100
    gross_profit_loss = quantity * price_change * quote_to_investment_rate
    opening_fee = position_notional * opening_fee_rate
    closing_fee = quantity * target_price * quote_to_investment_rate * closing_fee_rate
    total_fees = opening_fee + closing_fee + funding_fee
    net_profit_loss = gross_profit_loss - total_fees
    total_value_at_target = investment + net_profit_loss
    available_equity = investment - opening_fee - funding_fee + additional_margin
    close_and_maintenance_rate = maintenance_margin_rate + closing_fee_rate
    liquidation_price = None

    if side == "buy":
        denominator = quantity * quote_to_investment_rate * (1 - close_and_maintenance_rate)
        numerator = quantity * entry_price * quote_to_investment_rate - available_equity
        if denominator > 0 and numerator >= 0:
            liquidation_price = numerator / denominator
    else:
        denominator = quantity * quote_to_investment_rate * (1 + close_and_maintenance_rate)
        liquidation_price = (
            available_equity + quantity * entry_price * quote_to_investment_rate
        ) / denominator
        if liquidation_price <= 0:
            liquidation_price = None

    liquidation_distance = (
        None if liquidation_price is None else abs(entry_price - liquidation_price)
    )
    return PositionResult(
        side=side,
        entry_price=entry_price,
        target_price=target_price,
        investment=investment,
        leverage=leverage,
        quote_to_investment_rate=quote_to_investment_rate,
        position_notional=position_notional,
        quantity=quantity,
        price_change=price_change,
        price_change_percent=price_change_percent,
        return_percent=net_profit_loss / investment * 100,
        gross_profit_loss=gross_profit_loss,
        net_profit_loss=net_profit_loss,
        total_value_at_target=total_value_at_target,
        opening_fee=opening_fee,
        closing_fee=closing_fee,
        funding_fee=funding_fee,
        total_fees=total_fees,
        maintenance_margin_rate=maintenance_margin_rate,
        opening_fee_rate=opening_fee_rate,
        closing_fee_rate=closing_fee_rate,
        additional_margin=additional_margin,
        available_equity=available_equity,
        remaining_margin_buffer=(
            available_equity - position_notional * close_and_maintenance_rate
        ),
        liquidation_price=liquidation_price,
        liquidation_distance=liquidation_distance,
        liquidation_distance_percent=(
            None if liquidation_distance is None else liquidation_distance / entry_price * 100
        ),
    )


def calculate_position_with_deposit(
    position: PositionResult, deposit: float
) -> PositionResult:
    """Recalculate a position after adding a deposit to its existing margin."""
    if not isfinite(deposit) or deposit < 0:
        raise ValueError("Additional margin must be zero or a positive number.")
    return calculate_position(
        side=position.side,
        entry_price=position.entry_price,
        target_price=position.target_price,
        investment=position.investment,
        leverage=position.leverage,
        quote_to_investment_rate=position.quote_to_investment_rate,
        maintenance_margin_rate=position.maintenance_margin_rate,
        opening_fee_rate=position.opening_fee_rate,
        closing_fee_rate=position.closing_fee_rate,
        funding_fee=position.funding_fee,
        additional_margin=position.additional_margin + deposit,
    )


def calculate_additional_margin(position: PositionResult, stress_price: float) -> MarginResult:
    """Estimate the deposit needed to move liquidation beyond a stress price."""
    _assert_finite_positive(stress_price, "Stress price")
    liquidation_price = position.liquidation_price
    stress_is_valid = (
        liquidation_price is not None
        and (
            stress_price < liquidation_price
            if position.side == "buy"
            else stress_price > liquidation_price
        )
    )
    if not stress_is_valid:
        return MarginResult(
            valid=False,
            reason="Enter a price beyond the current estimated liquidation price.",
        )

    stress_notional = (
        position.quantity * stress_price * position.quote_to_investment_rate
    )
    stress_profit_loss = (
        position.quantity
        * (
            stress_price - position.entry_price
            if position.side == "buy"
            else position.entry_price - stress_price
        )
        * position.quote_to_investment_rate
    )
    liquidation_rate = position.maintenance_margin_rate + position.closing_fee_rate
    buffer_rate = 1 - liquidation_rate if position.side == "buy" else 1 + liquidation_rate
    required_equity = (
        stress_notional * liquidation_rate
        + position.quantity
        * position.quote_to_investment_rate
        * buffer_rate
        * SURVIVAL_BUFFER_PRICE
    )
    existing_equity = (
        position.investment
        - position.opening_fee
        - position.funding_fee
        + position.additional_margin
        + stress_profit_loss
    )
    additional_margin_required = max(0, required_equity - existing_equity)
    updated_position = calculate_position_with_deposit(position, additional_margin_required)
    total_margin_after_deposit = position.investment + updated_position.additional_margin
    return MarginResult(
        valid=True,
        stress_price=stress_price,
        additional_margin_required=additional_margin_required,
        total_margin_after_deposit=total_margin_after_deposit,
        effective_leverage=position.position_notional / total_margin_after_deposit,
        updated_position=updated_position,
        existing_equity_at_stress=existing_equity,
        required_equity_at_stress=required_equity,
    )
