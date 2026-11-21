# Investco

Streamlit calculator for linear perpetual positions. Estimate long/short profit or loss, fees, liquidation risk, and the money needed to survive a selected price.

Under **Save Liquidation**, enter either an additional margin amount to see
the new liquidation price, or an adverse asset price to estimate the required
margin. The two options are independent and both assume the deposit is made
before the original liquidation; they cannot restore an already liquidated position.
Both use the selected leverage and original trade size. Adding margin does not
open a larger position, so effective leverage (trade size divided by total margin)
decreases even though the selected exchange leverage setting stays the same.

Sidebar prices, initial margin, leverage, and funding amounts are whole numbers;
exchange rates and fee rates accept decimals. Money and prices in **Save Liquidation**
also accept decimals. Calculations retain precision, displayed results are rounded
to whole numbers except asset quantity, which is shown to five decimal places.
Required margin is rounded up to a whole investment-currency unit. Small prices
and quantities may display as zero, and rounded liquidation
and stress prices may appear equal.

## Run locally

```sh
python -m pip install -r requirements.txt
streamlit run app.py
```

Run the calculation tests with:

```sh
python -m unittest
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from the repository.
3. Set the main file path to `app.py` and deploy.

## Calculation assumptions

- Position notional is the initial investment multiplied by leverage. Quantity and P&L use the manually entered quote-to-investment currency rate.
- Target P&L is linear. Net results subtract estimated opening and closing fees and the one-time funding amount.
- Liquidation and additional-margin results use a simplified isolated-margin model that includes maintenance margin and estimated closing fees. A small price buffer is included when estimating additional margin.
- Exchange-specific tiers, mark-price rules, funding schedules, liquidation charges, and other account collateral are not modeled. Results are estimates, not exchange-accurate liquidation prices or financial advice.
