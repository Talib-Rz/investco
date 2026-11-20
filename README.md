# Investco

Responsive investment and leverage calculator for linear perpetual positions. Compare BUY/long and SELL/short outcomes, estimated liquidation risk, and additional margin scenarios.

## Run locally

```sh
npm start
```

Open [http://localhost:4173](http://localhost:4173). Run the calculation tests with:

```sh
npm test
```

## Download for offline use

Run `npm run build` to generate `/investco-mobile.html`, a self-contained copy of the calculator with its styles and calculation code embedded. Download that file to your phone and open it in a browser; it does not need a server or internet connection.

## Calculation assumptions

- Position notional is the initial margin multiplied by leverage. Quantity and P&L are converted between the asset quote currency and investment currency using the entered FX rate.
- Target P&L is linear. Net results subtract the configured opening fee, closing fee, and one-time funding amount.
- Liquidation and additional-margin results use a simplified isolated-margin model: equity is compared with maintenance margin and estimated closing fees. Additional margin includes a small price buffer so the recalculated liquidation level falls beyond the selected stress price.
- Cross-margin selection does not model other account collateral or open positions; results remain isolated-margin estimates. Auto top-up is not modeled.
- Exchange-specific tiers, mark-price rules, funding schedules, and liquidation charges are not implemented. Results are estimates, not exchange-accurate liquidation prices or financial advice.
