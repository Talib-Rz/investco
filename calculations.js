const SURVIVAL_BUFFER = 0.01;

function assertFinitePositive(value, label) {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${label} must be a positive number.`);
  }
}

function assertRate(value, label, maximum = 1) {
  if (!Number.isFinite(value) || value < 0 || value >= maximum) {
    throw new RangeError(`${label} must be at least 0 and less than ${maximum}.`);
  }
}

export function calculatePosition(input) {
  const {
    side,
    entryPrice,
    targetPrice,
    investment,
    leverage,
    quoteToInvestmentRate = 1,
    maintenanceMarginRate = 0.005,
    openingFeeRate = 0,
    closingFeeRate = 0,
    fundingFee = 0,
    additionalMargin = 0,
  } = input;

  if (side !== "buy" && side !== "sell") {
    throw new RangeError("Side must be buy or sell.");
  }
  assertFinitePositive(entryPrice, "Entry price");
  assertFinitePositive(targetPrice, "Target price");
  assertFinitePositive(investment, "Investment");
  assertFinitePositive(leverage, "Leverage");
  assertFinitePositive(quoteToInvestmentRate, "Exchange rate");
  assertRate(maintenanceMarginRate, "Maintenance margin rate");
  assertRate(openingFeeRate, "Opening fee rate");
  assertRate(closingFeeRate, "Closing fee rate");
  if (!Number.isFinite(fundingFee) || fundingFee < 0) {
    throw new RangeError("Funding fee must be zero or a positive number.");
  }
  if (!Number.isFinite(additionalMargin) || additionalMargin < 0) {
    throw new RangeError("Additional margin must be zero or a positive number.");
  }

  const positionNotional = investment * leverage;
  const quantity = positionNotional / (entryPrice * quoteToInvestmentRate);
  const priceChange = side === "buy" ? targetPrice - entryPrice : entryPrice - targetPrice;
  const priceChangePercent = (priceChange / entryPrice) * 100;
  const grossProfitLoss = quantity * priceChange * quoteToInvestmentRate;
  const openingFee = positionNotional * openingFeeRate;
  const closingFee = quantity * targetPrice * quoteToInvestmentRate * closingFeeRate;
  const totalFees = openingFee + closingFee + fundingFee;
  const netProfitLoss = grossProfitLoss - totalFees;
  const totalValueAtTarget = investment + netProfitLoss;
  const availableEquity = investment - openingFee - fundingFee + additionalMargin;
  const closeAndMaintenanceRate = maintenanceMarginRate + closingFeeRate;
  let liquidationPrice = null;

  if (side === "buy") {
    const denominator = quantity * quoteToInvestmentRate * (1 - closeAndMaintenanceRate);
    const numerator = quantity * entryPrice * quoteToInvestmentRate - availableEquity;
    if (denominator > 0 && numerator >= 0) {
      liquidationPrice = numerator / denominator;
    }
  } else {
    const denominator = quantity * quoteToInvestmentRate * (1 + closeAndMaintenanceRate);
    liquidationPrice = (availableEquity + quantity * entryPrice * quoteToInvestmentRate) / denominator;
    if (liquidationPrice <= 0) liquidationPrice = null;
  }

  const liquidationDistance = liquidationPrice === null
    ? null
    : Math.abs(entryPrice - liquidationPrice);

  return {
    side,
    entryPrice,
    targetPrice,
    investment,
    leverage,
    quoteToInvestmentRate,
    positionNotional,
    quantity,
    priceChange,
    priceChangePercent,
    returnPercent: (netProfitLoss / investment) * 100,
    grossProfitLoss,
    netProfitLoss,
    totalValueAtTarget,
    openingFee,
    closingFee,
    fundingFee,
    totalFees,
    maintenanceMarginRate,
    openingFeeRate,
    closingFeeRate,
    additionalMargin,
    availableEquity,
    remainingMarginBuffer: availableEquity - positionNotional * closeAndMaintenanceRate,
    liquidationPrice,
    liquidationDistance,
    liquidationDistancePercent: liquidationDistance === null ? null : (liquidationDistance / entryPrice) * 100,
  };
}

export function calculateAdditionalMargin(position, stressPrice) {
  assertFinitePositive(stressPrice, "Stress price");
  const { side, entryPrice, quantity, quoteToInvestmentRate, investment, leverage } = position;
  const stressIsValid = side === "buy"
    ? stressPrice < position.liquidationPrice
    : stressPrice > position.liquidationPrice;

  if (position.liquidationPrice === null || !stressIsValid) {
    return { valid: false, reason: "Enter a price beyond the current estimated liquidation price." };
  }

  const stressNotional = quantity * stressPrice * quoteToInvestmentRate;
  const stressProfitLoss = side === "buy"
    ? quantity * (stressPrice - entryPrice) * quoteToInvestmentRate
    : quantity * (entryPrice - stressPrice) * quoteToInvestmentRate;
  const requiredEquity = stressNotional
    * (position.maintenanceMarginRate + position.closingFeeRate)
    + SURVIVAL_BUFFER;
  const existingEquity = position.investment
    - position.openingFee
    - position.fundingFee
    + position.additionalMargin
    + stressProfitLoss;
  const additionalMarginRequired = Math.max(0, requiredEquity - existingEquity);
  const updatedPosition = calculatePosition({
    side,
    entryPrice,
    targetPrice: position.targetPrice,
    investment,
    leverage,
    quoteToInvestmentRate,
    maintenanceMarginRate: position.maintenanceMarginRate,
    openingFeeRate: position.openingFeeRate,
    closingFeeRate: position.closingFeeRate,
    fundingFee: position.fundingFee,
    additionalMargin: position.additionalMargin + additionalMarginRequired,
  });
  const totalMarginAfterDeposit = investment + updatedPosition.additionalMargin;

  return {
    valid: true,
    stressPrice,
    additionalMarginRequired,
    totalMarginAfterDeposit,
    effectiveLeverage: position.positionNotional / totalMarginAfterDeposit,
    updatedPosition,
    existingEquityAtStress: existingEquity,
    requiredEquityAtStress: requiredEquity,
  };
}
