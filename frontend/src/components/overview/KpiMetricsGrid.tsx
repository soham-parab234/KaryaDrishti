import React from 'react';
import type { OccupationSummary, PilotDistrict } from '../../types/lmis';
import {
  calculateAbsoluteGap,
  calculateGapRate,
  formatNumber,
  formatSignedNumber,
  formatGapRate,
} from '../../utils/calculations';

interface KpiMetricsGridProps {
  occupations: OccupationSummary[];
  selectedDistrict: PilotDistrict;
  selectedSector?: string;
}

export const KpiMetricsGrid: React.FC<KpiMetricsGridProps> = ({
  occupations,
  selectedDistrict,
  selectedSector = 'ALL',
}) => {
  // Filter occupations
  const filtered = occupations.filter((o) => {
    if (selectedDistrict !== 'All Districts' && o.district !== selectedDistrict) return false;
    if (selectedSector !== 'ALL' && o.sector !== selectedSector) return false;
    return true;
  });

  const totalDemand = filtered.reduce((acc, curr) => acc + curr.documentedDemand, 0);
  const totalSupply = filtered.reduce((acc, curr) => acc + curr.qualifiedSupply, 0);
  const totalSeats = filtered.reduce((acc, curr) => acc + curr.trainingCapacity, 0);
  const netGap = calculateAbsoluteGap(totalDemand, totalSupply);
  const netGapRate = calculateGapRate(totalDemand, totalSupply);

  const isShortage = netGap > 0;
  const isSurplus = netGap < 0;

  return (
    <section className="indicators-ledger" aria-label="Key Labour Market Indicator Ledger">
      {/* 1. Documented Demand Signals */}
      <div className="ledger-cell">
        <span className="ledger-label">Documented Demand Signals</span>
        <div className="ledger-num-row">
          <span className="ledger-number">{formatNumber(totalDemand)}</span>
          <span className="ledger-badge neutral">Postings</span>
        </div>
        <div className="ledger-desc">
          Aggregated employer hiring indicators across monitored portals.
        </div>
        <div className="ledger-guardrail">
          Definition: Documented postings · Not total vacancies
        </div>
      </div>

      {/* 2. Qualified Supply Estimate */}
      <div className="ledger-cell">
        <span className="ledger-label">Qualified Supply Estimate</span>
        <div className="ledger-num-row">
          <span className="ledger-number">{formatNumber(totalSupply)}</span>
          <span className="ledger-badge balanced">Available</span>
        </div>
        <div className="ledger-desc">
          Estimated pool of plausibly qualified and active workers.
        </div>
        <div className="ledger-guardrail">
          Seats separated: {formatNumber(totalSeats)} sanctioned training seats
        </div>
      </div>

      {/* 3. Net Projected Labour Gap */}
      <div className="ledger-cell">
        <span className="ledger-label">Net Projected Labour Gap</span>
        <div className="ledger-num-row">
          <span
            className="ledger-number"
            style={{ color: isShortage ? '#c2410c' : isSurplus ? '#4338ca' : '#15803d' }}
          >
            {formatSignedNumber(netGap)}
          </span>
          <span className={`ledger-badge ${isShortage ? 'shortage' : isSurplus ? 'surplus' : 'balanced'}`}>
            {formatGapRate(netGapRate)}
          </span>
        </div>
        <div className="ledger-desc">
          {isShortage
            ? 'Shortage Signal: Observed demand exceeds qualified supply estimate.'
            : isSurplus
            ? 'Oversupply Signal: Qualified supply estimate exceeds observed demand.'
            : 'Balanced Signal: Demand signals roughly match qualified supply.'}
        </div>
        <div className="ledger-guardrail">
          Formula: (Demand − Supply) / Demand × 100
        </div>
      </div>

      {/* 4. Forecast Engine Status */}
      <div className="ledger-cell">
        <span className="ledger-label">Baseline Forecast Engine</span>
        <div className="ledger-num-row">
          <span className="ledger-number" style={{ fontSize: '20px', color: '#0f766e' }}>
            3M-MA Baseline
          </span>
          <span className="ledger-badge neutral">Active</span>
        </div>
        <div className="ledger-desc">
          Evaluated via rolling-origin holdouts (strictly no future leakage).
        </div>
        <div className="ledger-guardrail">
          Scope: 3 Occupations · 2 Districts (MH Pilot)
        </div>
      </div>
    </section>
  );
};
