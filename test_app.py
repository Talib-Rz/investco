import re
import unittest
from math import ceil

from streamlit.testing.v1 import AppTest

from calculations import calculate_additional_margin, calculate_position, calculate_position_with_deposit


def calculate(app):
    next(button for button in app.button if button.label == "Calculate trade").click().run()
    return app


class MarginProtectionAppTests(unittest.TestCase):
    def test_results_require_calculation_and_reset_after_edit(self):
        app = AppTest.from_file("app.py").run()
        self.assertFalse(app.tabs)
        self.assertFalse(app.metric)
        calculate(app)
        self.assertEqual([tab.label for tab in app.tabs], ["Trade summary", "Save Liquidation"])
        original = next(m.value for m in app.metric if m.label == "Net profit / loss")
        app.number_input(key="entry_price").set_value(4000).run()
        self.assertFalse(app.tabs)
        calculate(app)
        self.assertNotEqual(original, next(m.value for m in app.metric if m.label == "Net profit / loss"))
        app.number_input[3].set_value(100.0)
        calculate(app)
        self.assertTrue(app.error)
        self.assertFalse(app.tabs)
        app.number_input[3].set_value(0.5).run()
        self.assertFalse(app.tabs)
        calculate(app)
        self.assertFalse(app.error)
        self.assertTrue(app.tabs)

    def test_calculate_buttons_recalculate_and_preserve_results(self):
        app = calculate(AppTest.from_file("app.py").run())
        original_pnl = next(m.value for m in app.metric if m.label == "Net profit / loss")
        app.number_input[0].set_value(4000)
        next(button for button in app.button if button.label == "Calculate trade").click().run()
        self.assertFalse(app.exception)
        self.assertNotEqual(
            original_pnl, next(m.value for m in app.metric if m.label == "Net profit / loss")
        )
        app.text_input(key="deposit").set_value("1000")
        app.button(key="calculate_deposit").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.label == "New liquidation price" for m in app.metric))
        app.text_input(key="stress").set_value("2500")
        app.button(key="calculate_stress").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.label == "Money to add" for m in app.metric))
        self.assertTrue(any(m.label == "New liquidation price" for m in app.metric))

    def test_deposit_and_stress_price_work_independently_for_both_sides(self):
        for side, stress in (("BUY · Long", "2500"), ("SELL · Short", "5000")):
            with self.subTest(side=side):
                app = AppTest.from_file("app.py").run()
                app.radio[0].set_value(side).run()
                if side.startswith("SELL"):
                    app.number_input(key="target_price").set_value(2500).run()
                calculate(app)
                app.text_input(key="stress").set_value(stress).run()
                self.assertFalse(app.exception)
                required = next(m.value for m in app.metric if m.label == "Money to add")
                app.text_input(key="deposit").set_value("1000").run()
                self.assertFalse(app.exception)
                self.assertEqual(
                    next(m.value for m in app.metric if m.label == "Money to add"),
                    required,
                )
                self.assertTrue(any("Total money: ₹36,000" in c.value for c in app.caption))
                self.assertEqual(sum(m.label == "New liquidation price" for m in app.metric), 1)

    def test_invalid_deposits_and_no_positive_level(self):
        app = calculate(AppTest.from_file("app.py").run())
        for value in ("bad", "-1", "nan", "inf"):
            with self.subTest(deposit=value):
                app.text_input(key="deposit").set_value(value).run()
                self.assertFalse(app.exception)
                self.assertTrue(any("Additional margin" in warning.value for warning in app.warning))
                self.assertFalse(any(m.label == "New liquidation price" for m in app.metric))
        app.text_input(key="deposit").set_value("200000").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.value == "Not available" for m in app.metric))

    def test_whole_number_output_and_rounded_up_required_margin(self):
        app = calculate(AppTest.from_file("app.py").run())
        app.text_input(key="stress").set_value("2500.25").run()
        self.assertFalse(app.exception)
        position = calculate_position(
            side="buy", entry_price=3500, target_price=5000, investment=35000,
            leverage=5, quote_to_investment_rate=83.5, maintenance_margin_rate=0.005,
        )
        result = calculate_additional_margin(position, 2500.25)
        required = ceil(result.additional_margin_required)
        funded = calculate_position_with_deposit(position, required)
        self.assertEqual(
            next(m.value for m in app.metric if m.label == "Money to add"),
            f"₹{required:,}",
        )
        self.assertTrue(any(
            f"New liquidation price: ${round(funded.liquidation_price):,}" in c.value
            for c in app.caption
        ))
        for metric in app.metric:
            self.assertNotRegex(metric.value, r"\d\.\d", metric.label)
        for table in app.table:
            rows = table.value
            for _, row in rows.iterrows():
                if row["Metric"] != "Asset quantity":
                    self.assertFalse(re.search(r"\d\.\d", row["Value"]))

    def test_whole_trade_inputs_and_no_scenarios(self):
        app = calculate(AppTest.from_file("app.py").run())
        original_pnl = next(m.value for m in app.metric if m.label == "Net profit / loss")
        app.number_input[0].set_value(3501).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input[0].value, 3501)
        calculate(app)
        self.assertNotEqual(
            original_pnl, next(m.value for m in app.metric if m.label == "Net profit / loss")
        )
        self.assertEqual([tab.label for tab in app.tabs], ["Trade summary", "Save Liquidation"])
        for field in (app.number_input[0], app.number_input[1], app.number_input[2], app.number_input[-1]):
            self.assertIsInstance(field.value, int)
        self.assertIsInstance(app.slider[0].value, int)
        self.assertEqual(app.text_input(key="fx-INR-USD").value, "83.5")
        self.assertEqual(app.number_input[3].value, 0.5)

    def test_asset_quantity_shows_five_decimal_places(self):
        app = calculate(AppTest.from_file("app.py").run())
        self.assertFalse(app.exception)
        position = calculate_position(
            side="buy", entry_price=3500, target_price=5000, investment=35000,
            leverage=5, quote_to_investment_rate=83.5, maintenance_margin_rate=0.005,
        )
        rows = app.table[0].value
        quantity = rows.loc[rows["Metric"] == "Asset quantity", "Value"].iloc[0]
        self.assertEqual(quantity, f"{position.quantity:,.5f} units")
        self.assertNotEqual(quantity, "0.00000 units")

    def test_selected_leverage_applies_to_both_protection_options(self):
        for side, side_label, stress in (("buy", "BUY · Long", 2500), ("sell", "SELL · Short", 5000)):
            for leverage in (5, 10):
                with self.subTest(side=side, leverage=leverage):
                    app = AppTest.from_file("app.py").run()
                    app.radio[0].set_value(side_label)
                    if side == "sell":
                        app.number_input(key="target_price").set_value(2500)
                    app.slider[0].set_value(leverage).run()
                    calculate(app)
                    app.text_input(key="deposit").set_value("1000")
                    app.text_input(key="stress").set_value(str(stress)).run()
                    self.assertFalse(app.exception)
                    position = calculate_position(
                        side=side, entry_price=3500, target_price=5000 if side == "buy" else 2500, investment=35000,
                        leverage=leverage, quote_to_investment_rate=83.5,
                        maintenance_margin_rate=0.005,
                    )
                    deposited = calculate_position_with_deposit(position, 1000)
                    result = calculate_additional_margin(position, stress)
                    self.assertTrue(result.valid)
                    required = ceil(result.additional_margin_required)
                    funded = calculate_position_with_deposit(position, required)
                    self.assertEqual(
                        next(m.value for m in app.metric if m.label == "New liquidation price"),
                        f"${round(deposited.liquidation_price):,}",
                    )
                    self.assertEqual(
                        next(m.value for m in app.metric if m.label == "Money to add"),
                        f"₹{required:,}",
                    )
                    self.assertTrue(any(
                        f"New liquidation price: ${round(funded.liquidation_price):,}" in c.value
                        for c in app.caption
                    ))
                    self.assertTrue(any(f"selected {leverage}× leverage" in c.value for c in app.caption))

    def test_exchange_rate_validation(self):
        app = AppTest.from_file("app.py").run()
        for value in ("", "bad", "0", "nan"):
            with self.subTest(value=value):
                app.text_input(key="fx-INR-USD").set_value(value).run()
                calculate(app)
                self.assertFalse(app.exception)
                self.assertTrue(app.error)
        app.text_input(key="fx-INR-USD").set_value("83.25").run()
        calculate(app)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)

    def test_target_direction_guardrails(self):
        for side, invalid_targets, valid_target, message in (
            ("BUY · Long", (3500, 3000), 4000, "higher"),
            ("SELL · Short", (3500, 4000), 3000, "lower"),
        ):
            for target in invalid_targets:
                with self.subTest(side=side, target=target):
                    app = AppTest.from_file("app.py").run()
                    app.radio[0].set_value(side)
                    app.number_input(key="target_price").set_value(target).run()
                    calculate(app)
                    self.assertFalse(app.exception)
                    self.assertFalse(app.tabs)
                    self.assertTrue(any(message in error.value for error in app.error))
                    app.number_input(key="target_price").set_value(valid_target).run()
                    calculate(app)
                    self.assertFalse(app.error)
                    self.assertTrue(app.tabs)

    def test_fee_guardrails_and_unprofitable_target_warning(self):
        app = AppTest.from_file("app.py").run()
        app.number_input[3].set_value(50.0)
        app.number_input[5].set_value(50.0).run()
        calculate(app)
        self.assertFalse(app.tabs)
        self.assertTrue(any("total less than 100%" in error.value for error in app.error))
        app.number_input[3].set_value(20.0)
        app.number_input[5].set_value(0.0).run()
        calculate(app)
        self.assertFalse(app.tabs)
        self.assertTrue(any("at or beyond liquidation" in error.value for error in app.error))
        app.number_input[3].set_value(0.5)
        app.number_input(key="target_price").set_value(3501)
        app.number_input[4].set_value(0.1).run()
        calculate(app)
        self.assertFalse(app.error)
        self.assertTrue(any("unprofitable" in warning.value for warning in app.warning))

    def test_currency_changes_preserve_amounts_and_conversion(self):
        app = AppTest.from_file("app.py").run()
        app.number_input(key="entry_price").set_value(4000)
        app.number_input(key="target_price").set_value(6000)
        app.number_input(key="investment").set_value(12345)
        app.selectbox(key="quote_currency").select("USDT").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key="entry_price").value, 4000)
        self.assertEqual(app.number_input(key="target_price").value, 6000)
        self.assertEqual(app.number_input(key="target_price").label, "Target price (USDT)")
        self.assertEqual(app.number_input(key="investment").value, 12345)
        calculate(app)
        self.assertTrue(any("exchange rate" in item.value.lower() for item in app.error))
        app.text_input(key="fx-INR-USDT").set_value("83.5").run()
        self.assertFalse(app.error)
        app.selectbox(key="investment_currency").select("USDT").run()
        calculate(app)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.number_input(key="entry_price").value, 4000)
        self.assertEqual(app.number_input(key="investment").value, 12345)
        self.assertTrue(any("₮" in metric.value for metric in app.metric))

    def test_price_labels_currency_and_short_price_movement(self):
        app = AppTest.from_file("app.py").run()
        self.assertEqual(app.number_input(key="entry_price").label, "Buy price")
        app.number_input(key="entry_price").set_value(4000)
        app.number_input(key="target_price").set_value(3000)
        app.radio[0].set_value("SELL · Short").run()
        self.assertEqual(app.number_input(key="entry_price").label, "Sell price")
        self.assertEqual(app.number_input(key="entry_price").value, 4000)
        self.assertEqual(app.number_input(key="target_price").value, 3000)
        app.selectbox(key="quote_currency").select("EUR").run()
        self.assertEqual(app.number_input(key="target_price").label, "Target price (EUR)")
        self.assertEqual(app.number_input(key="entry_price").value, 4000)
        self.assertEqual(app.number_input(key="target_price").value, 3000)
        app.text_input(key="fx-INR-EUR").set_value("90").run()
        calculate(app)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        rows = app.table[0].value.set_index("Metric")["Value"]
        self.assertEqual(rows["Sell price"], "€4,000")
        self.assertEqual(rows["Target price"], "€3,000")
        self.assertEqual(rows["Price movement"], "−€1,000 (-25%)")
        self.assertTrue(next(m.value for m in app.metric if m.label == "Estimated liquidation price").startswith("€"))
        self.assertEqual(app.text_input(key="stress").label, "Price to survive (EUR)")
        app.radio[0].set_value("BUY · Long").run()
        self.assertEqual(app.number_input(key="entry_price").label, "Buy price")
        self.assertEqual(app.number_input(key="entry_price").value, 4000)
        self.assertEqual(app.number_input(key="target_price").value, 3000)


if __name__ == "__main__":
    unittest.main()
