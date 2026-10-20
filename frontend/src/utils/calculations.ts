/**
 * Pure calculation utilities, domain metrics, and real forecast evaluation
 * Source of truth: LMIS Master R&D Sections 8, 9, 10 & AI Handoff
 *
 * MANDATORY CORRECTION COMPLIANCE:
 * - All evaluation metrics (MAE, RMSE, MAPE) are calculated from actual time-series logic.
 * - If evaluation has not been performed or data is insufficient, returns explicit
 *   'INSUFFICIENT_DATA' or 'NOT_EVALUATED' states with null metrics.
 */

import type { RiskLevel, ForecastModelEvaluation, ScenarioParameters, ScenarioResult } from '../types/lmis';

/**
 * Calculate Absolute Gap
 * Formula: Demand - Qualified Supply
 * Positive = Potential Shortage
 * Negative = Potential Oversupply
 */
export function calculateAbsoluteGap(demand: number, qualifiedSupply: number): number {
  return demand - qualifiedSupply;
}

/**
 * Calculate Gap Rate Percentage
 * Formula: ((Demand - Qualified Supply) / Demand) * 100
 * Guardrail: Undefined (returns null) when demand <= 0 to avoid false precision.
 */
export function calculateGapRate(demand: number, qualifiedSupply: number): number | null {
  if (demand <= 0) {
    return null;
  }
  const gap = calculateAbsoluteGap(demand, qualifiedSupply);
  return Number(((gap / demand) * 100).toFixed(1));
}

/**
 * Determine risk level based on gap rate and evidence
 */
export function determineRiskLevel(demand: number, qualifiedSupply: number): RiskLevel {
  if (demand <= 0 && qualifiedSupply <= 0) {
    return 'INSUFFICIENT_DATA';
  }

  const gapRate = calculateGapRate(demand, qualifiedSupply);
  if (gapRate === null) {
    return 'INSUFFICIENT_DATA';
  }

  if (gapRate >= 25) {
    return 'CRITICAL_SHORTAGE';
  } else if (gapRate > 5) {
    return 'MODERATE_SHORTAGE';
  } else if (gapRate < -15) {
    return 'POTENTIAL_OVERSUPPLY';
  } else {
    return 'BALANCED';
  }
}

/**
 * Format numbers with Indian / international commas
 */
export function formatNumber(val: number): string {
  return new Intl.NumberFormat('en-IN').format(val);
}

/**
 * Format signed numbers (e.g. +180, -90)
 */
export function formatSignedNumber(val: number): string {
  const prefix = val > 0 ? '+' : '';
  return `${prefix}${formatNumber(val)}`;
}

/**
 * Format gap rate as percentage or 'N/A' if null
 */
export function formatGapRate(rate: number | null): string {
  if (rate === null) return 'N/A (0 Demand)';
  const prefix = rate > 0 ? '+' : '';
  return `${prefix}${rate.toFixed(1)}%`;
}

/**
 * Calculate Training Seat Scenario Results
 * Adheres strictly to Master R&D Section 10 formula:
 * Scenario Entrants = Seats × Enrolment Rate × Completion Rate × Target Role/Geography Entry Rate
 */
export function calculateScenarioResult(
  baselineShortage: number,
  params: ScenarioParameters
): ScenarioResult {
  const yieldPerSeat = (params.enrolmentRate / 100) * (params.completionRate / 100) * (params.localEntryRate / 100);
  const expectedQualifiedEntrants = Math.round(params.proposedSeats * yieldPerSeat);
  const residualGap = baselineShortage - expectedQualifiedEntrants;
  
  const gapReductionPercent = baselineShortage > 0
    ? Math.min(100, Math.max(0, Number((((baselineShortage - residualGap) / baselineShortage) * 100).toFixed(1))))
    : 0;

  const instructorsNeeded = Math.ceil(params.proposedSeats / (params.trainerRatioRequired || 20));
  const estimatedBudget = params.proposedSeats * (params.unitCostPerSeat || 18500);

  let feasibilityWarning: string | undefined;
  if (params.proposedSeats > 500) {
    feasibilityWarning = 'High seat expansion (>500): Verify accredited workshop infrastructure and trainer availability before allocation.';
  } else if (residualGap < -100) {
    feasibilityWarning = 'Surplus warning: Proposed seats may exceed absorption capacity, creating localized oversupply of certificate holders.';
  }

  return {
    yieldPerSeat,
    expectedQualifiedEntrants,
    baselineGap: baselineShortage,
    residualGap,
    gapReductionPercent,
    instructorsNeeded,
    estimatedBudget,
    feasibilityWarning,
  };
}

/**
 * REAL FORECAST EVALUATION ENGINE (Chronological Holdout)
 * 
 * Takes an actual historical series of numbers, splits into training window and holdout test points,
 * generates rolling step-ahead predictions using the specified model, and computes actual MAE, RMSE, MAPE.
 * Zero future data leakage!
 */
export function evaluateChronologicalHoldout(
  historicalValues: number[],
  modelType: 'BASELINE_MA' | 'NAIVE_LAST' | 'LINEAR_DRIFT' | 'CANDIDATE_ETS' | 'CANDIDATE_ARIMA',
  targetSeriesName: string,
  holdoutCount: number = 3
): ForecastModelEvaluation {
  // Guardrail: Minimum 6 points needed to have at least 3 train points and holdout points
  if (!historicalValues || historicalValues.length < holdoutCount + 3) {
    return {
      modelName: getModelDisplayName(modelType),
      modelType,
      targetSeries: targetSeriesName,
      evaluationStatus: 'INSUFFICIENT_DATA',
      holdoutPeriodsCount: 0,
      calculatedMae: null,
      calculatedRmse: null,
      calculatedMape: null,
      evaluationWindow: 'None (Insufficient history)',
      modelVerdict: 'Insufficient observations for holdout validation (requires >= 6 monthly points).',
      caveat: 'Time series too sparse. Baseline moving average default applied without statistical guarantee.',
    };
  }

  // Unimplemented candidate models return NOT_EVALUATED
  if (modelType === 'CANDIDATE_ARIMA' || modelType === 'CANDIDATE_ETS') {
    return {
      modelName: getModelDisplayName(modelType),
      modelType,
      targetSeries: targetSeriesName,
      evaluationStatus: 'NOT_EVALUATED',
      holdoutPeriodsCount: holdoutCount,
      calculatedMae: null,
      calculatedRmse: null,
      calculatedMape: null,
      evaluationWindow: `Last ${holdoutCount} periods (Unfitted)`,
      modelVerdict: 'Not evaluated. Advanced ML/ARIMA candidate models require external python statsmodels verification.',
      caveat: 'Do not use un-evaluated candidate models for policy planning until validated against baseline.',
    };
  }

  const trainLength = historicalValues.length - holdoutCount;
  const actuals: number[] = [];
  const predictions: number[] = [];

  for (let i = 0; i < holdoutCount; i++) {
    const testIndex = trainLength + i;
    const actual = historicalValues[testIndex];
    actuals.push(actual);

    // Available series strictly prior to testIndex
    const availablePrior = historicalValues.slice(0, testIndex);

    let pred = 0;
    if (modelType === 'BASELINE_MA') {
      // 3-Period Moving Average prior to testIndex
      const window = availablePrior.slice(-3);
      pred = Math.round(window.reduce((a, b) => a + b, 0) / window.length);
    } else if (modelType === 'NAIVE_LAST') {
      // Last observed value
      pred = availablePrior[availablePrior.length - 1];
    } else if (modelType === 'LINEAR_DRIFT') {
      // Naïve plus average historical change
      const first = availablePrior[0];
      const last = availablePrior[availablePrior.length - 1];
      const avgChange = (last - first) / (availablePrior.length - 1);
      pred = Math.round(last + avgChange);
    }

    predictions.push(pred);
  }

  // Compute real metrics
  let sumAbsError = 0;
  let sumSqError = 0;
  let sumPctError = 0;

  for (let i = 0; i < holdoutCount; i++) {
    const error = actuals[i] - predictions[i];
    sumAbsError += Math.abs(error);
    sumSqError += error * error;
    sumPctError += Math.abs(error / actuals[i]);
  }

  const mae = Number((sumAbsError / holdoutCount).toFixed(1));
  const rmse = Number(Math.sqrt(sumSqError / holdoutCount).toFixed(1));
  const mape = Number(((sumPctError / holdoutCount) * 100).toFixed(1));

  return {
    modelName: getModelDisplayName(modelType),
    modelType,
    targetSeries: targetSeriesName,
    evaluationStatus: 'EVALUATED',
    holdoutPeriodsCount: holdoutCount,
    calculatedMae: mae,
    calculatedRmse: rmse,
    calculatedMape: mape,
    evaluationWindow: `Periods t-${holdoutCount} to t-1 (Chronological split)`,
    modelVerdict: `Evaluated over ${holdoutCount} held-out periods. MAE = ${mae} units (${mape}% error).`,
    caveat: 'Evaluated strictly on historical observations. Does not guarantee future structural stability.',
  };
}

function getModelDisplayName(type: ForecastModelEvaluation['modelType']): string {
  switch (type) {
    case 'BASELINE_MA':
      return '3-Month Moving Average (Baseline)';
    case 'NAIVE_LAST':
      return 'Naïve Last Value';
    case 'LINEAR_DRIFT':
      return 'Linear Drift Baseline';
    case 'CANDIDATE_ETS':
      return 'Candidate ETS / Holt-Winters';
    case 'CANDIDATE_ARIMA':
      return 'Candidate ARIMA(1,1,0)';
  }
}
