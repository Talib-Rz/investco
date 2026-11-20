import test from "node:test";
import assert from "node:assert/strict";
import { calculateAdditionalMargin, calculatePosition } from "../calculations.js";

function base(overrides = {}) {
  return {
    side: "buy",
    entryPrice: 3500,
    targetPrice: 5000,
    investment: 35000,
    leverage: 5,
    maintenanceMarginRate: 0,
    openingFeeRate: 0,
    closingFeeRate: 0,
    fundingFee: 0,
    ...overrides,
  };
}

test("BUY profit matches the illustrative example before fees", () => {
  const result = calculatePosition(base());
  assert.equal(result.positionNotional, 175000);
  assert.equal(result.quantity, 50);
  assert.equal(result.priceChangePercent, 100 * 1500 / 3500);
  assert.equal(result.grossProfitLoss, 75000);
  assert.equal(result.netProfitLoss, 75000);
  assert.equal(result.returnPercent, 100 * 75000 / 35000);
  assert.equal(result.totalValueAtTarget, 110000);
});

test("BUY loss is shown as a negative return", () => {
  const result = calculatePosition(base({ targetPrice: 2500 }));
  assert.equal(result.grossProfitLoss, -50000);
  assert.equal(result.returnPercent, -100 * 50000 / 35000);
  assert.equal(result.totalValueAtTarget, -15000);
});

test("SELL profit matches the illustrative example before fees", () => {
  const result = calculatePosition(base({ side: "sell", targetPrice: 2500 }));
  assert.equal(result.quantity, 50);
  assert.equal(result.priceChangePercent, 1000 / 3500 * 100);
  assert.equal(result.grossProfitLoss, 50000);
  assert.equal(result.returnPercent, 100 * 50000 / 35000);
  assert.equal(result.totalValueAtTarget, 85000);
});

test("SELL loss is negative when the target rises", () => {
  const result = calculatePosition(base({ side: "sell", targetPrice: 5000 }));
  assert.equal(result.grossProfitLoss, -75000);
  assert.equal(result.returnPercent, -100 * 75000 / 35000);
});

test("position size and quantity account for quote currency conversion", () => {
  const result = calculatePosition(base({
    entryPrice: 100,
    targetPrice: 110,
    investment: 1000,
    leverage: 2,
    quoteToInvestmentRate: 10,
  }));
  assert.equal(result.positionNotional, 2000);
  assert.equal(result.quantity, 2);
  assert.equal(result.grossProfitLoss, 200);
});

test("liquidation prices include maintenance margin and estimated closing fees", () => {
  const common = {
    entryPrice: 1000,
    targetPrice: 1000,
    investment: 100,
    leverage: 5,
    maintenanceMarginRate: 0.01,
    closingFeeRate: 0.005,
  };
  const buy = calculatePosition(base(common));
  const sell = calculatePosition(base({ ...common, side: "sell" }));
  assert.ok(buy.liquidationPrice < 1000);
  assert.ok(sell.liquidationPrice > 1000);
  assert.ok(Math.abs(buy.liquidationPrice - 800 / 0.985) < 1e-10);
  assert.ok(Math.abs(sell.liquidationPrice - 1200 / 1.015) < 1e-10);
});

test("additional margin moves BUY liquidation below the selected stress price", () => {
  const position = calculatePosition(base({
    entryPrice: 1000,
    targetPrice: 1100,
    investment: 100,
    leverage: 5,
    maintenanceMarginRate: 0.01,
    closingFeeRate: 0.005,
  }));
  const result = calculateAdditionalMargin(position, 700);
  assert.equal(result.valid, true);
  assert.ok(result.additionalMarginRequired > 0);
  assert.ok(result.updatedPosition.liquidationPrice < 700);
  assert.ok(result.updatedPosition.additionalMargin > 0);
});

test("additional margin moves SELL liquidation above the selected stress price", () => {
  const position = calculatePosition(base({
    side: "sell",
    entryPrice: 1000,
    targetPrice: 900,
    investment: 100,
    leverage: 5,
    maintenanceMarginRate: 0.01,
    closingFeeRate: 0.005,
  }));
  const result = calculateAdditionalMargin(position, 1300);
  assert.equal(result.valid, true);
  assert.ok(result.additionalMarginRequired > 0);
  assert.ok(result.updatedPosition.liquidationPrice > 1300);
});

test("increasing stress severity increases additional margin in both directions", () => {
  const long = calculatePosition(base({
    entryPrice: 1000, targetPrice: 1100, investment: 100, leverage: 5, maintenanceMarginRate: 0.01,
  }));
  const short = calculatePosition(base({
    side: "sell", entryPrice: 1000, targetPrice: 900, investment: 100, leverage: 5, maintenanceMarginRate: 0.01,
  }));
  const lessSevereLong = calculateAdditionalMargin(long, 790);
  const moreSevereLong = calculateAdditionalMargin(long, 700);
  const lessSevereShort = calculateAdditionalMargin(short, 1210);
  const moreSevereShort = calculateAdditionalMargin(short, 1300);
  assert.ok(moreSevereLong.additionalMarginRequired > lessSevereLong.additionalMarginRequired);
  assert.ok(moreSevereShort.additionalMarginRequired > lessSevereShort.additionalMarginRequired);
  assert.ok(moreSevereLong.updatedPosition.liquidationPrice < lessSevereLong.updatedPosition.liquidationPrice);
  assert.ok(moreSevereShort.updatedPosition.liquidationPrice > lessSevereShort.updatedPosition.liquidationPrice);
});

test("fees and funding reduce net results and liquidation equity", () => {
  const result = calculatePosition(base({
    openingFeeRate: 0.001,
    closingFeeRate: 0.002,
    fundingFee: 300,
  }));
  assert.equal(result.openingFee, 175);
  assert.equal(result.closingFee, 500);
  assert.equal(result.totalFees, 975);
  assert.equal(result.netProfitLoss, 74025);
  assert.equal(result.availableEquity, 34525);
  assert.ok(result.liquidationPrice > 0);
});

test("adding margin and recalculating lowers long liquidation and raises short liquidation", () => {
  for (const side of ["buy", "sell"]) {
    const position = calculatePosition(base({
      side,
      entryPrice: 1000,
      targetPrice: side === "buy" ? 1100 : 900,
      investment: 100,
      leverage: 5,
      maintenanceMarginRate: 0.01,
    }));
    const added = calculatePosition({ ...base({
      side,
      entryPrice: 1000,
      targetPrice: side === "buy" ? 1100 : 900,
      investment: 100,
      leverage: 5,
      maintenanceMarginRate: 0.01,
      additionalMargin: 25,
    }) });
    if (side === "buy") assert.ok(added.liquidationPrice < position.liquidationPrice);
    else assert.ok(added.liquidationPrice > position.liquidationPrice);
  }
});

test("1x leverage still applies the configured maintenance model", () => {
  const result = calculatePosition(base({
    entryPrice: 100,
    targetPrice: 100,
    investment: 100,
    leverage: 1,
    maintenanceMarginRate: 0.01,
  }));
  assert.equal(result.liquidationPrice, 0);
});

test("invalid inputs and a stress price on the safe side are rejected", () => {
  assert.throws(() => calculatePosition(base({ investment: 0 })), /Investment/);
  assert.throws(() => calculatePosition(base({ entryPrice: -1 })), /Entry price/);
  assert.throws(() => calculatePosition(base({ leverage: 0 })), /Leverage/);
  assert.throws(() => calculatePosition(base({ maintenanceMarginRate: 1 })), /Maintenance/);
  const position = calculatePosition(base({
    entryPrice: 100,
    targetPrice: 110,
    investment: 100,
    leverage: 5,
    maintenanceMarginRate: 0.01,
  }));
  assert.equal(calculateAdditionalMargin(position, position.liquidationPrice + 1).valid, false);
  assert.throws(() => calculateAdditionalMargin(position, 0), /Stress price/);
});
