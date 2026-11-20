import { calculateAdditionalMargin, calculatePosition } from "./calculations.js";

const byId = (id) => document.getElementById(id);
const currencySymbols = { INR: "₹", USD: "$", USDT: "₮", EUR: "€", GBP: "£" };
const state = { side: "buy", lastMarginResult: null, fxPair: "INR/USD" };
const fields = {
  asset: byId("asset-name"),
  entry: byId("entry-price"),
  target: byId("target-price"),
  investment: byId("investment"),
  investmentCurrency: byId("investment-currency"),
  leverage: byId("leverage"),
  customLeverage: byId("leverage-custom"),
  quoteCurrency: byId("quote-currency"),
  exchangeRate: byId("exchange-rate"),
  maintenanceRate: byId("maintenance-rate"),
  openingFee: byId("opening-fee"),
  closingFee: byId("closing-fee"),
  fundingFee: byId("funding-fee"),
  marginMode: byId("margin-mode"),
  stressPrice: byId("stress-price"),
  scenarioPrices: byId("scenario-prices"),
};

function readNumber(input) {
  return input.value.trim() === "" ? Number.NaN : Number(input.value);
}

function currencyFormatter(currency, digits = 2) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function money(value, currency, digits = 2) {
  if (!Number.isFinite(value)) return "—";
  return currencyFormatter(currency, digits).format(Math.abs(value) < 0.0000001 ? 0 : value);
}

function priceMoney(value, currency) {
  return money(value, currency, 6);
}

function signedMoney(value, currency, digits = 2) {
  if (!Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${money(Math.abs(value), currency, digits)}`;
}

function signedPercent(value, digits = 2) {
  if (!Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(digits)}%`;
}

function plainNumber(value, digits = 4) {
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}

function currentLeverage() {
  const custom = readNumber(fields.customLeverage);
  return Number.isFinite(custom) ? custom : Number(fields.leverage.value);
}

function updateCurrencyLabels() {
  const investmentCurrency = fields.investmentCurrency.value;
  const quoteCurrency = fields.quoteCurrency.value;
  const sameCurrency = investmentCurrency === quoteCurrency;
  const rate = byId("exchange-rate");
  const pair = `${investmentCurrency}/${quoteCurrency}`;
  byId("investment-symbol").textContent = currencySymbols[investmentCurrency] || investmentCurrency;
  byId("funding-symbol").textContent = currencySymbols[investmentCurrency] || investmentCurrency;
  byId("quote-symbol").textContent = currencySymbols[quoteCurrency] || quoteCurrency;
  byId("target-symbol").textContent = currencySymbols[quoteCurrency] || quoteCurrency;
  byId("stress-symbol").textContent = currencySymbols[quoteCurrency] || quoteCurrency;
  byId("quote-currency-label").textContent = quoteCurrency;
  byId("fx-caption").textContent = `${investmentCurrency} per 1 ${quoteCurrency}`;
  if (sameCurrency) {
    rate.value = "1";
    rate.disabled = true;
  } else {
    if (rate.disabled || state.fxPair !== pair) rate.value = "";
    rate.disabled = false;
  }
  state.fxPair = pair;
}

function setText(id, value) {
  byId(id).textContent = value;
}

function setClass(element, className, active) {
  element.classList.toggle(className, active);
}

function clearCalculation(error) {
  byId("form-error").textContent = error;
  byId("form-error").hidden = false;
  state.position = null;
  state.lastMarginResult = null;
  byId("margin-results").hidden = true;
  byId("stress-error").hidden = true;
  [
    "result-investment", "result-notional", "result-quantity", "result-prices",
    "result-price-currencies", "result-net-pnl", "result-net-return", "result-price-move",
    "result-gross-pnl", "result-fees", "result-total-value", "result-liquidation",
    "liq-distance", "result-liq-move", "result-liq-percent", "result-available-equity",
    "result-margin-buffer", "result-margin-ratio",
  ].forEach((id) => setText(id, "—"));
  renderPriceMap(null, null);
  renderScenarios(null, null);
}

function readPositionInputs() {
  const investmentCurrency = fields.investmentCurrency.value;
  const quoteCurrency = fields.quoteCurrency.value;
  const exchangeRate = readNumber(fields.exchangeRate);
  if (investmentCurrency === quoteCurrency) fields.exchangeRate.value = "1";
  const position = calculatePosition({
    side: state.side,
    entryPrice: readNumber(fields.entry),
    targetPrice: readNumber(fields.target),
    investment: readNumber(fields.investment),
    leverage: currentLeverage(),
    quoteToInvestmentRate: investmentCurrency === quoteCurrency ? 1 : exchangeRate,
    maintenanceMarginRate: readNumber(fields.maintenanceRate) / 100,
    openingFeeRate: readNumber(fields.openingFee) / 100,
    closingFeeRate: readNumber(fields.closingFee) / 100,
    fundingFee: readNumber(fields.fundingFee),
  });
  if (position.leverage > 100) throw new RangeError("Leverage cannot exceed 100×.");
  if (readNumber(fields.maintenanceRate) >= 100
    || readNumber(fields.openingFee) >= 100
    || readNumber(fields.closingFee) >= 100) {
    throw new RangeError("Margin and fee rates must be less than 100%.");
  }
  return position;
}

function renderPosition(position) {
  const investmentCurrency = fields.investmentCurrency.value;
  const quoteCurrency = fields.quoteCurrency.value;
  const asset = fields.asset.value.trim();
  const positive = position.netProfitLoss >= 0;
  const movePositive = position.priceChange >= 0;
  const ratio = position.investment / position.positionNotional * 100;
  const value = (id) => byId(id);

  setText("asset-title", asset || "Your position");
  setText("direction-pill", state.side === "buy" ? "BUY · LONG" : "SELL · SHORT");
  value("direction-pill").className = `direction-pill ${state.side === "buy" ? "buy-pill" : "sell-pill"}`;
  setText("result-investment", money(position.investment, investmentCurrency));
  setText("result-notional", money(position.positionNotional, investmentCurrency));
  setText("result-leverage", `At ${plainNumber(position.leverage, 2)}× leverage`);
  setText("result-quantity", plainNumber(position.quantity, 8));
  setText("quantity-asset", `${asset || "Asset"} units`);
  setText("result-prices", `${priceMoney(position.entryPrice, quoteCurrency)} → ${priceMoney(position.targetPrice, quoteCurrency)}`);
  setText("result-price-currencies", `${quoteCurrency} quote`);

  setText("result-net-pnl", signedMoney(position.netProfitLoss, investmentCurrency));
  setText("result-net-return", signedPercent(position.returnPercent));
  setText("result-price-move", `${signedMoney(position.priceChange, quoteCurrency, 6)} (${signedPercent(position.priceChangePercent)})`);
  setText("result-gross-pnl", signedMoney(position.grossProfitLoss, investmentCurrency));
  setText("result-fees", `−${money(position.totalFees, investmentCurrency)}`);
  setText("result-total-value", money(position.totalValueAtTarget, investmentCurrency));
  setClass(value("result-net-pnl"), "negative", !positive);
  setClass(value("result-net-return"), "negative", !positive);
  setClass(value("result-price-move"), "negative", !movePositive);
  setClass(value("result-gross-pnl"), "negative", position.grossProfitLoss < 0);
  value("target-symbol-icon").classList.toggle("negative", !positive);
  value("target-symbol-icon").textContent = positive ? "↗" : "↘";

  setText("liq-direction", `Estimated ${state.side === "buy" ? "long" : "short"} liquidation price`);
  if (position.liquidationPrice === null) {
    setText("result-liquidation", "No positive level");
    setText("liq-distance", "No positive liquidation price in this simplified model");
    setText("result-liq-move", "—");
    setText("result-liq-percent", "—");
  } else {
    const movement = state.side === "buy"
      ? position.entryPrice - position.liquidationPrice
      : position.liquidationPrice - position.entryPrice;
    setText("result-liquidation", priceMoney(position.liquidationPrice, quoteCurrency));
    setText("liq-distance", `${priceMoney(position.liquidationDistance, quoteCurrency)} from entry price`);
    setText("result-liq-move", `${priceMoney(movement, quoteCurrency)} ${state.side === "buy" ? "drop" : "rise"}`);
    setText("result-liq-percent", `${position.liquidationDistancePercent.toFixed(2)}% ${state.side === "buy" ? "drop" : "rise"}`);
  }
  setText("result-available-equity", money(position.availableEquity, investmentCurrency));
  setText("result-margin-buffer", money(position.remainingMarginBuffer, investmentCurrency));
  setClass(byId("result-margin-buffer"), "negative", position.remainingMarginBuffer < 0);
  setText("result-margin-ratio", `${ratio.toFixed(2)}%`);
  value("util-fill").style.width = `${Math.max(0, Math.min(100, ratio))}%`;
  value("direction-pill").className = `direction-pill ${state.side === "buy" ? "buy-pill" : "sell-pill"}`;
  value("risk-notice").classList.toggle("warning", fields.marginMode.value === "cross");
  value("risk-notice").textContent = fields.marginMode.value === "cross"
    ? "Cross margin selected: this display remains an isolated-margin estimate. Other collateral and open positions can materially change cross-margin liquidation."
    : "Simplified linear isolated-margin estimate. Actual exchange liquidation can differ due to mark price, fee tiers, risk limits, funding, and exchange rules.";
  setText("settings-footnote", `${byId("auto-topup").value === "on" ? "Auto top-up is selected but not modeled. " : ""}Funding is entered as a one-time amount in your investment currency.`);

  const direction = state.side === "buy" ? "Below liquidation" : "Above liquidation";
  setText("target-direction", `${state.side.toUpperCase()} target`);
  setText("stress-direction", direction);
  setText("scenario-hint", direction.toLowerCase());
  state.position = position;
  byId("form-error").hidden = true;
  renderMargin();
}

function buildMarker(label, value, currency, positionPercent, className) {
  const marker = document.createElement("div");
  marker.className = `price-marker ${className}`;
  if (positionPercent < 9) marker.classList.add("label-left");
  if (positionPercent > 91) marker.classList.add("label-right");
  marker.style.left = `${positionPercent}%`;
  marker.setAttribute("aria-label", `${label}: ${priceMoney(value, currency)}`);
  const line = document.createElement("span");
  line.className = "marker-line";
  const dot = document.createElement("span");
  dot.className = "marker-dot";
  const labelWrap = document.createElement("span");
  labelWrap.className = "marker-label";
  const name = document.createElement("small");
  name.textContent = label;
  const price = document.createElement("strong");
  price.textContent = priceMoney(value, currency);
  labelWrap.append(name, price);
  marker.append(line, dot, labelWrap);
  return marker;
}

function renderPriceMap(position, marginResult) {
  const container = byId("price-markers");
  container.replaceChildren();
  if (!position) {
    setText("plot-range", "Updates with your position");
    return;
  }
  const quoteCurrency = fields.quoteCurrency.value;
  const levels = [
    { label: "Entry", value: position.entryPrice, className: "marker-entry" },
    { label: "Target", value: position.targetPrice, className: `marker-target${position.priceChange < 0 ? " marker-loss" : ""}` },
  ];
  if (position.liquidationPrice !== null) {
    levels.push({ label: "Liquidation", value: position.liquidationPrice, className: "marker-liquidation" });
  }
  if (Number.isFinite(readNumber(fields.stressPrice))) {
    levels.push({ label: "Stress", value: readNumber(fields.stressPrice), className: "marker-stress" });
  }
  if (marginResult?.valid && marginResult.additionalMarginRequired > 0) {
    levels.push({ label: "New liquidation", value: marginResult.updatedPosition.liquidationPrice, className: "marker-new-liquidation" });
  }
  const prices = levels.map((level) => level.value);
  let minimum = Math.min(...prices);
  let maximum = Math.max(...prices);
  if (minimum === maximum) {
    minimum *= 0.95;
    maximum *= 1.05;
  }
  const range = maximum - minimum;
  levels.forEach((level) => {
    const positionPercent = 5 + ((level.value - minimum) / range) * 90;
    container.append(buildMarker(level.label, level.value, quoteCurrency, positionPercent, level.className));
  });
  setText("plot-range", `${priceMoney(minimum, quoteCurrency)} — ${priceMoney(maximum, quoteCurrency)}`);
}

function renderMargin() {
  const position = state.position;
  if (!position || fields.stressPrice.value.trim() === "") {
    byId("stress-error").hidden = true;
    byId("margin-results").hidden = true;
    state.lastMarginResult = null;
    renderPriceMap(position, null);
    renderScenarios(position, null);
    return;
  }
  const quoteCurrency = fields.quoteCurrency.value;
  const investmentCurrency = fields.investmentCurrency.value;
  try {
    const stressPrice = readNumber(fields.stressPrice);
    const marginResult = calculateAdditionalMargin(position, stressPrice);
    if (!marginResult.valid) {
      byId("stress-error").textContent = marginResult.reason;
      byId("stress-error").hidden = false;
      byId("margin-results").hidden = true;
      state.lastMarginResult = null;
      renderPriceMap(position, null);
      renderScenarios(position, null);
      return;
    }
    byId("stress-error").hidden = true;
    byId("margin-results").hidden = false;
    state.lastMarginResult = marginResult;
    setText("result-add-margin", money(marginResult.additionalMarginRequired, investmentCurrency));
    setText("result-new-liq", marginResult.updatedPosition.liquidationPrice === null
      ? "No positive level"
      : priceMoney(marginResult.updatedPosition.liquidationPrice, quoteCurrency));
    setText("result-total-margin", money(marginResult.totalMarginAfterDeposit, investmentCurrency));
    setText("result-effective-leverage", `${plainNumber(marginResult.effectiveLeverage, 2)}×`);

    const oldMargin = position.investment + position.additionalMargin;
    const oldLeverage = position.positionNotional / oldMargin;
    const oldBuffer = position.liquidationPrice === null ? null : Math.abs(position.entryPrice - position.liquidationPrice);
    const newLiq = marginResult.updatedPosition.liquidationPrice;
    const newBuffer = newLiq === null ? null : Math.abs(position.entryPrice - newLiq);
    setText("compare-old-liq", position.liquidationPrice === null ? "—" : priceMoney(position.liquidationPrice, quoteCurrency));
    setText("compare-new-liq", newLiq === null ? "—" : priceMoney(newLiq, quoteCurrency));
    setText("compare-old-margin", money(oldMargin, investmentCurrency));
    setText("compare-new-margin", money(marginResult.totalMarginAfterDeposit, investmentCurrency));
    setText("compare-old-leverage", `${plainNumber(oldLeverage, 2)}×`);
    setText("compare-new-leverage", `${plainNumber(marginResult.effectiveLeverage, 2)}×`);
    setText("compare-old-buffer", oldBuffer === null ? "—" : money(oldBuffer, quoteCurrency));
    setText("compare-new-buffer", newBuffer === null ? "—" : money(newBuffer, quoteCurrency));
    byId("sufficiency-note").hidden = marginResult.additionalMarginRequired > 0;
    renderPriceMap(position, marginResult);
    renderScenarios(position, marginResult);
  } catch (error) {
    byId("stress-error").textContent = error.message;
    byId("stress-error").hidden = false;
    byId("margin-results").hidden = true;
    state.lastMarginResult = null;
    renderPriceMap(position, null);
    renderScenarios(position, null);
  }
}

function defaultScenarioPrices(position) {
  if (position.liquidationPrice === null) return [];
  const factors = position.side === "buy"
    ? [0.98, 0.95, 0.9, 0.8, 0.7]
    : [1.02, 1.05, 1.1, 1.2, 1.3];
  return factors.map((factor) => position.liquidationPrice * factor);
}

function renderScenarios(position, primaryResult) {
  const rows = byId("scenario-rows");
  rows.replaceChildren();
  if (!position || position.liquidationPrice === null) {
    addEmptyScenario("A positive liquidation estimate is needed for scenarios.");
    return;
  }
  const entered = fields.scenarioPrices.value.trim();
  const prices = entered === ""
    ? defaultScenarioPrices(position)
    : entered.split(",").map((part) => part.trim() === "" ? Number.NaN : Number(part)).slice(0, 8);
  const quoteCurrency = fields.quoteCurrency.value;
  const investmentCurrency = fields.investmentCurrency.value;
  prices.forEach((price) => {
    const row = document.createElement("tr");
    if (!Number.isFinite(price) || price <= 0) {
      const error = document.createElement("td");
      error.colSpan = 3;
      error.className = "empty-row";
      error.textContent = "Enter positive prices separated by commas.";
      row.append(error);
      rows.append(row);
      return;
    }
    const result = calculateAdditionalMargin(position, price);
    const priceCell = document.createElement("td");
    const marginCell = document.createElement("td");
    const newLiquidationCell = document.createElement("td");
    priceCell.textContent = priceMoney(price, quoteCurrency);
    if (!result.valid) {
      marginCell.textContent = "Not beyond liquidation";
      newLiquidationCell.textContent = "—";
    } else {
      marginCell.textContent = money(result.additionalMarginRequired, investmentCurrency);
      newLiquidationCell.textContent = result.updatedPosition.liquidationPrice === null
        ? "—"
        : priceMoney(result.updatedPosition.liquidationPrice, quoteCurrency);
      if (result.additionalMarginRequired === 0 && primaryResult?.stressPrice === price) {
        marginCell.textContent = "Already covered";
      }
    }
    row.append(priceCell, marginCell, newLiquidationCell);
    rows.append(row);
  });
  if (prices.length === 0) addEmptyScenario("No scenario prices available.");
}

function addEmptyScenario(message) {
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 3;
  cell.className = "empty-row";
  cell.textContent = message;
  row.append(cell);
  byId("scenario-rows").append(row);
}

function recalculate() {
  updateCurrencyLabels();
  setText("leverage-value", `${plainNumber(currentLeverage(), 2)}×`);
  document.querySelectorAll(".side-option").forEach((button) => {
    const selected = button.dataset.side === state.side;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  byId("direction-pill").className = `direction-pill ${state.side === "buy" ? "buy-pill" : "sell-pill"}`;
  byId("direction-pill").textContent = state.side === "buy" ? "BUY · LONG" : "SELL · SHORT";
  try {
    const position = readPositionInputs();
    renderPosition(position);
    renderPriceMap(position, state.lastMarginResult);
    renderScenarios(position, state.lastMarginResult);
  } catch (error) {
    clearCalculation(error.message);
  }
}

document.querySelectorAll(".side-option").forEach((button) => {
  button.addEventListener("click", () => {
    state.side = button.dataset.side;
    fields.stressPrice.value = "";
    recalculate();
  });
});

fields.leverage.addEventListener("input", () => {
  fields.customLeverage.value = "";
  recalculate();
});
fields.customLeverage.addEventListener("input", recalculate);
fields.investmentCurrency.addEventListener("change", recalculate);
fields.quoteCurrency.addEventListener("change", recalculate);
Object.values(fields).forEach((field) => {
  if (field === fields.leverage || field === fields.customLeverage
    || field === fields.investmentCurrency || field === fields.quoteCurrency) return;
  field.addEventListener("input", recalculate);
  field.addEventListener("change", recalculate);
});
byId("theme-toggle").addEventListener("click", () => {
  const dark = document.body.classList.toggle("dark");
  byId("theme-toggle").setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  byId("theme-toggle").title = dark ? "Switch to light theme" : "Switch to dark theme";
});

recalculate();
