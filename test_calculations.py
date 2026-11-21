import unittest

from calculations import (
    calculate_additional_margin,
    calculate_position,
    calculate_position_with_deposit,
)


def base(**overrides):
    values = {
        "side": "buy",
        "entry_price": 3500,
        "target_price": 5000,
        "investment": 35000,
        "leverage": 5,
        "maintenance_margin_rate": 0,
        "opening_fee_rate": 0,
        "closing_fee_rate": 0,
        "funding_fee": 0,
    }
    values.update(overrides)
    return calculate_position(**values)


class PositionCalculationTests(unittest.TestCase):
    def test_buy_profit_before_fees(self):
        result = base()
        self.assertEqual(result.position_notional, 175000)
        self.assertEqual(result.quantity, 50)
        self.assertAlmostEqual(result.price_change_percent, 100 * 1500 / 3500)
        self.assertEqual(result.gross_profit_loss, 75000)
        self.assertEqual(result.net_profit_loss, 75000)
        self.assertEqual(result.return_percent, 100 * 75000 / 35000)
        self.assertEqual(result.total_value_at_target, 110000)

    def test_buy_loss_is_negative(self):
        result = base(target_price=2500)
        self.assertEqual(result.gross_profit_loss, -50000)
        self.assertEqual(result.return_percent, -100 * 50000 / 35000)
        self.assertEqual(result.total_value_at_target, -15000)

    def test_sell_profit_and_loss(self):
        profit = base(side="sell", target_price=2500)
        loss = base(side="sell", target_price=5000)
        self.assertEqual(profit.quantity, 50)
        self.assertEqual(profit.gross_profit_loss, 50000)
        self.assertEqual(profit.total_value_at_target, 85000)
        self.assertEqual(loss.gross_profit_loss, -75000)
        self.assertEqual(loss.return_percent, -100 * 75000 / 35000)

    def test_quote_currency_conversion(self):
        result = calculate_position(
            side="buy",
            entry_price=100,
            target_price=110,
            investment=1000,
            leverage=2,
            quote_to_investment_rate=10,
        )
        self.assertEqual(result.position_notional, 2000)
        self.assertEqual(result.quantity, 2)
        self.assertEqual(result.gross_profit_loss, 200)

    def test_liquidation_includes_maintenance_and_closing_fees(self):
        common = {
            "entry_price": 1000,
            "target_price": 1000,
            "investment": 100,
            "leverage": 5,
            "maintenance_margin_rate": 0.01,
            "closing_fee_rate": 0.005,
        }
        buy = calculate_position(side="buy", **common)
        sell = calculate_position(side="sell", **common)
        self.assertAlmostEqual(buy.liquidation_price, 800 / 0.985)
        self.assertAlmostEqual(sell.liquidation_price, 1200 / 1.015)

    def test_additional_margin_moves_liquidation_beyond_stress_price(self):
        buy = calculate_additional_margin(
            base(
                entry_price=1000,
                target_price=1100,
                investment=100,
                leverage=5,
                maintenance_margin_rate=0.01,
                closing_fee_rate=0.005,
            ),
            700,
        )
        sell = calculate_additional_margin(
            base(
                side="sell",
                entry_price=1000,
                target_price=900,
                investment=100,
                leverage=5,
                maintenance_margin_rate=0.01,
                closing_fee_rate=0.005,
            ),
            1300,
        )
        self.assertTrue(buy.valid)
        self.assertGreater(buy.additional_margin_required, 0)
        self.assertLess(buy.updated_position.liquidation_price, 700)
        self.assertTrue(sell.valid)
        self.assertGreater(sell.additional_margin_required, 0)
        self.assertGreater(sell.updated_position.liquidation_price, 1300)

    def test_more_severe_stress_requires_more_margin(self):
        long = base(
            entry_price=1000,
            target_price=1100,
            investment=100,
            leverage=5,
            maintenance_margin_rate=0.01,
        )
        short = base(
            side="sell",
            entry_price=1000,
            target_price=900,
            investment=100,
            leverage=5,
            maintenance_margin_rate=0.01,
        )
        less_severe_long = calculate_additional_margin(long, 790)
        more_severe_long = calculate_additional_margin(long, 700)
        less_severe_short = calculate_additional_margin(short, 1210)
        more_severe_short = calculate_additional_margin(short, 1300)
        self.assertGreater(
            more_severe_long.additional_margin_required,
            less_severe_long.additional_margin_required,
        )
        self.assertGreater(
            more_severe_short.additional_margin_required,
            less_severe_short.additional_margin_required,
        )

    def test_fees_and_funding_reduce_net_results_and_equity(self):
        result = base(
            opening_fee_rate=0.001,
            closing_fee_rate=0.002,
            funding_fee=300,
        )
        self.assertEqual(result.opening_fee, 175)
        self.assertEqual(result.closing_fee, 500)
        self.assertEqual(result.total_fees, 975)
        self.assertEqual(result.net_profit_loss, 74025)
        self.assertEqual(result.available_equity, 34525)

    def test_extra_margin_moves_liquidation_away_from_entry(self):
        for side in ("buy", "sell"):
            initial = base(
                side=side,
                entry_price=1000,
                target_price=1100 if side == "buy" else 900,
                investment=100,
                leverage=5,
                maintenance_margin_rate=0.01,
            )
            funded = calculate_position(
                side=side,
                entry_price=1000,
                target_price=1100 if side == "buy" else 900,
                investment=100,
                leverage=5,
                maintenance_margin_rate=0.01,
                additional_margin=25,
            )
            if side == "buy":
                self.assertLess(funded.liquidation_price, initial.liquidation_price)
            else:
                self.assertGreater(funded.liquidation_price, initial.liquidation_price)

    def test_deposit_to_liquidation_for_long_and_short(self):
        for side, expected in (("buy", 750 / 0.985), ("sell", 1250 / 1.015)):
            with self.subTest(side=side):
                position = calculate_position(
                    side=side,
                    entry_price=1000,
                    target_price=1100,
                    investment=100,
                    leverage=5,
                    maintenance_margin_rate=0.01,
                    closing_fee_rate=0.005,
                )
                updated = calculate_position_with_deposit(position, 25)
                self.assertAlmostEqual(updated.liquidation_price, expected)
                self.assertEqual(updated.additional_margin, 25)
                self.assertEqual(position.additional_margin, 0)
                self.assertEqual(updated.position_notional, position.position_notional)
                self.assertEqual(updated.net_profit_loss, position.net_profit_loss)

    def test_deposit_accumulates_and_handles_no_positive_level(self):
        position = base(
            entry_price=100, target_price=110, investment=100, leverage=2,
            additional_margin=10,
        )
        self.assertEqual(calculate_position_with_deposit(position, 0), position)
        updated = calculate_position_with_deposit(position, 100)
        self.assertEqual(updated.additional_margin, 110)
        self.assertIsNone(updated.liquidation_price)
        for value in (-1, float("nan"), float("inf")):
            with self.subTest(deposit=value), self.assertRaisesRegex(ValueError, "Additional margin"):
                calculate_position_with_deposit(position, value)

    def test_required_deposit_matches_deposit_calculation_with_fx_and_fees(self):
        for side, stress in (("buy", 700), ("sell", 1300)):
            with self.subTest(side=side):
                position = calculate_position(
                    side=side,
                    entry_price=1000,
                    target_price=1100,
                    investment=100,
                    leverage=5,
                    quote_to_investment_rate=10,
                    maintenance_margin_rate=0.01,
                    opening_fee_rate=0.001,
                    closing_fee_rate=0.005,
                    funding_fee=2,
                    additional_margin=5,
                )
                result = calculate_additional_margin(position, stress)
                self.assertTrue(result.valid)
                updated = calculate_position_with_deposit(
                    position, result.additional_margin_required
                )
                self.assertEqual(updated, result.updated_position)
                if side == "buy":
                    self.assertLess(updated.liquidation_price, stress)
                else:
                    self.assertGreater(updated.liquidation_price, stress)

    def test_one_x_leverage_keeps_the_maintenance_model(self):
        result = base(
            entry_price=100,
            target_price=100,
            investment=100,
            leverage=1,
            maintenance_margin_rate=0.01,
        )
        self.assertEqual(result.liquidation_price, 0)

    def test_invalid_inputs_and_unsafe_stress_price(self):
        with self.assertRaisesRegex(ValueError, "Investment"):
            base(investment=0)
        with self.assertRaisesRegex(ValueError, "Entry price"):
            base(entry_price=-1)
        with self.assertRaisesRegex(ValueError, "Leverage"):
            base(leverage=0)
        with self.assertRaisesRegex(ValueError, "Maintenance"):
            base(maintenance_margin_rate=1)
        position = base(
            entry_price=100,
            target_price=110,
            investment=100,
            leverage=5,
            maintenance_margin_rate=0.01,
        )
        result = calculate_additional_margin(position, position.liquidation_price + 1)
        self.assertFalse(result.valid)
        with self.assertRaisesRegex(ValueError, "Stress price"):
            calculate_additional_margin(position, 0)

    def test_invalid_margin_and_leverage_conditions_are_rejected(self):
        for side in ("buy", "sell"):
            for margin_rate, closing_rate in ((0.6, 0.4), (0.7, 0.4)):
                with self.subTest(side=side, maintenance=margin_rate, closing=closing_rate):
                    with self.assertRaisesRegex(ValueError, "total less than 100%"):
                        base(side=side, maintenance_margin_rate=margin_rate, closing_fee_rate=closing_rate)
            for margin_rate in (0.2, 0.3):
                with self.subTest(side=side, maintenance=margin_rate):
                    with self.assertRaisesRegex(ValueError, "at or beyond liquidation"):
                        base(side=side, maintenance_margin_rate=margin_rate)
        for leverage in (0.5, 101):
            with self.subTest(leverage=leverage):
                with self.assertRaisesRegex(ValueError, "between 1 and 100"):
                    base(leverage=leverage)
        with self.assertRaisesRegex(ValueError, "at or beyond liquidation"):
            base(funding_fee=35000)

    def test_extreme_rates_and_stress_values_fail_explicitly(self):
        for rate in (5e-324, 1e308):
            with self.subTest(rate=rate):
                with self.assertRaisesRegex(ValueError, "too large or too small"):
                    base(quote_to_investment_rate=rate)
        position = base(side="sell", target_price=2500)
        with self.assertRaisesRegex(ValueError, "too large or too small"):
            calculate_additional_margin(position, 1e308)


if __name__ == "__main__":
    unittest.main()
