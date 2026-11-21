import re
import unittest
from math import ceil

from streamlit.testing.v1 import AppTest

from calculations import calculate_additional_margin, calculate_position, calculate_position_with_deposit


class MarginProtectionAppTests(unittest.TestCase):
    def test_deposit_and_stress_price_work_independently_for_both_sides(self):
        for side, stress in (("BUY · Long", "2500"), ("SELL · Short", "5000")):
            with self.subTest(side=side):
                app = AppTest.from_file("app.py").run()
                app.radio[0].set_value(side).run()
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
        app = AppTest.from_file("app.py").run()
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
        app = AppTest.from_file("app.py").run()
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

    def test_whole_sidebar_inputs_and_no_scenarios(self):
        app = AppTest.from_file("app.py").run()
        original_pnl = next(m.value for m in app.metric if m.label == "Net profit / loss")
        app.number_input[0].set_value(3501).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input[0].value, 3501)
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
        app = AppTest.from_file("app.py").run()
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
                    app.slider[0].set_value(leverage)
                    app.text_input(key="deposit").set_value("1000")
                    app.text_input(key="stress").set_value(str(stress)).run()
                    self.assertFalse(app.exception)
                    position = calculate_position(
                        side=side, entry_price=3500, target_price=5000, investment=35000,
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
                self.assertFalse(app.exception)
                self.assertTrue(app.error)
        app.text_input(key="fx-INR-USD").set_value("83.25").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)


if __name__ == "__main__":
    unittest.main()
