import React, { useState, useEffect } from 'react';
import {
  Sliders,
  AlertCircle,
  Building,
  RotateCcw,
  ShieldCheck,
  Cpu,
  Compass,
  ArrowRight,
  TrendingUp,
  BookOpen,
  FileSearch,
} from 'lucide-react';

import { SYNTHETIC_OCCUPATIONS } from '../../data/syntheticData';
import {
  calculateScenarioResult,
  formatNumber,
  formatSignedNumber,
} from '../../utils/calculations';
import type { PilotDistrict, ScenarioParameters, ScenarioResult, PolicyRecommendation } from '../../types/lmis';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { apiClient } from '../../services/apiClient';
import type { BackendScenarioResponse } from '../../services/apiClient';

interface ScenarioPlannerViewProps {
  selectedDistrict: PilotDistrict;
  selectedSector?: string;
}

interface TradeOption {
  id: string;
  ncoCode: string;
  canonicalTitle: string;
  district: string;
  districtCode: string;
  baselineGap: number;
}

export const ScenarioPlannerView: React.FC<ScenarioPlannerViewProps> = ({ selectedDistrict }) => {
  const [tradeOptions, setTradeOptions] = useState<TradeOption[]>(() =>
    SYNTHETIC_OCCUPATIONS.map((occ) => ({
      id: occ.id,
      ncoCode: occ.ncoCode,
      canonicalTitle: occ.canonicalTitle,
      district: occ.district,
      districtCode: occ.district === 'Pune' ? 'MH_PUN' : 'MH_NSK',
      baselineGap: occ.absoluteGap,
    }))
  );

  const [selectedOccId, setSelectedOccId] = useState<string>('occ-solar-pune');
  const [recommendations, setRecommendations] = useState<PolicyRecommendation[]>([]);
  const [selectedRecFilter, setSelectedRecFilter] = useState<string>('ALL');
  const [isRecsLoading, setIsRecsLoading] = useState<boolean>(true);

  // Load dynamic occupations and baseline gaps from backend
  useEffect(() => {
    let isMounted = true;
    apiClient
      .getGaps()
      .then((gaps) => {
        if (!isMounted || !gaps || gaps.length === 0) return;
        const options: TradeOption[] = gaps.map((g) => ({
          id: `${g.nco_code}-${g.district_code}`,
          ncoCode: g.nco_code,
          canonicalTitle: g.canonical_title || `NCO ${g.nco_code}`,
          district: g.district_code === 'MH_PUN' ? 'Pune' : g.district_code === 'MH_NSK' ? 'Nashik' : g.district_code,
          districtCode: g.district_code,
          baselineGap: g.absolute_gap,
        }));
        setTradeOptions(options);
      })
      .catch(() => {
        // Fallback to synthetic occupations
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Load decision intelligence recommendations from backend
  useEffect(() => {
    let isMounted = true;
    apiClient
      .getRecommendations()
      .then((res) => {
        if (!isMounted) return;
        setRecommendations(res.items || []);
        setIsRecsLoading(false);
      })
      .catch(() => {
        if (!isMounted) return;
        setIsRecsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredTradeOptions = tradeOptions.filter((t) => {
    if (selectedDistrict === 'All Districts') return true;
    return t.district.toLowerCase() === selectedDistrict.toLowerCase();
  });

  const activeTrade =
    filteredTradeOptions.find((t) => t.id === selectedOccId) ||
    filteredTradeOptions[0] ||
    tradeOptions[0];

  const baselineShortage = activeTrade ? activeTrade.baselineGap : 350;

  const [params, setParams] = useState<ScenarioParameters>({
    targetOccupationId: activeTrade?.id || 'occ-solar-pune',
    proposedSeats: 350,
    enrolmentRate: 90,
    completionRate: 85,
    localEntryRate: 70,
    trainerRatioRequired: 20,
    unitCostPerSeat: 18500,
  });

  const [backendResult, setBackendResult] = useState<BackendScenarioResponse | null>(null);
  const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);

  // Invoke backend scenario planner endpoint on parameter changes
  useEffect(() => {
    let isMounted = true;
    const runCalculation = async () => {
      if (!activeTrade) return;
      try {
        const res = await apiClient.calculateScenario({
          nco_code: activeTrade.ncoCode,
          district_code: activeTrade.districtCode,
          reporting_period: '2026-10',
          baseline_gap: baselineShortage,
          proposed_additional_seats: params.proposedSeats,
          enrolment_rate_pct: params.enrolmentRate,
          completion_rate_pct: params.completionRate,
          local_entry_rate_pct: params.localEntryRate,
          estimated_cost_per_seat_inr: params.unitCostPerSeat,
          trainee_trainer_ratio: params.trainerRatioRequired,
        });
        if (isMounted) {
          setBackendResult(res);
          setIsLiveBackend(true);
        }
      } catch {
        if (isMounted) {
          setIsLiveBackend(false);
          setBackendResult(null);
        }
      }
    };
    runCalculation();
    return () => {
      isMounted = false;
    };
  }, [activeTrade, baselineShortage, params]);

  // Use backend calculations when live, or fallback to client utility
  const fallbackResult: ScenarioResult = calculateScenarioResult(baselineShortage, params);

  const yieldPerSeat = backendResult ? backendResult.effective_yield_per_seat : fallbackResult.yieldPerSeat;
  const expectedQualifiedEntrants = backendResult ? backendResult.scenario_entrants : fallbackResult.expectedQualifiedEntrants;
  const residualGap = backendResult ? backendResult.residual_gap : fallbackResult.residualGap;
  const gapReductionPercent = backendResult ? backendResult.gap_reduction_pct : fallbackResult.gapReductionPercent;
  const estimatedBudget = backendResult ? backendResult.estimated_budget_inr : fallbackResult.estimatedBudget;
  const instructorsNeeded = backendResult ? backendResult.estimated_trainers_required : fallbackResult.instructorsNeeded;

  const comparisonChartData = [
    {
      name: 'Baseline Need',
      workers: baselineShortage,
      fill: baselineShortage >= 0 ? '#c2410c' : '#0369a1',
    },
    {
      name: 'Scenario Supply',
      workers: expectedQualifiedEntrants,
      fill: '#0d9488',
    },
    {
      name: 'Residual Gap',
      workers: Math.max(0, residualGap),
      fill: residualGap <= 0 ? '#15803d' : '#e11d48',
    },
  ];

  // Handler to load a recommendation into the scenario simulator
  const handleApplyRecommendation = (rec: PolicyRecommendation) => {
    // Find matching trade in options
    const match = tradeOptions.find(
      (t) => t.ncoCode === rec.nco_code && (t.districtCode === rec.district_code || t.district.toLowerCase().includes(rec.district_code.toLowerCase()))
    );
    if (match) {
      setSelectedOccId(match.id);
    }
    if (rec.proposed_seat_adjustment > 0) {
      setParams((prev) => ({
        ...prev,
        proposedSeats: rec.proposed_seat_adjustment,
      }));
    }
    // Scroll down smoothly to the levers section
    const el = document.getElementById('scenario-simulator-levers');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const filteredRecs = recommendations.filter((r) => {
    if (selectedRecFilter !== 'ALL' && r.recommendation_type !== selectedRecFilter) return false;
    if (selectedDistrict !== 'All Districts') {
      const distMatch = r.district_code === 'MH_PUN' || r.district_code === 'MH-PUN' ? 'Pune' : 'Nashik';
      if (distMatch !== selectedDistrict) return false;
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Editorial Header */}
      <div className="editorial-card" style={{ padding: '20px 24px', borderLeft: '4px solid #c2410c' }}>
        <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <h2>Decision Intelligence &amp; Training-Seat Scenario Simulator</h2>
            <span className="data-status-tag" style={{ fontSize: '10px' }}>
              {isLiveBackend ? 'CALCULATION ENGINE ACTIVE' : 'SCENARIO SIMULATION MODE'}
            </span>
          </div>
          <div className="heading-accent-bar"></div>
          <p>
            Bridging labor market forecasts with actionable policy: Review evidence-based training recommendations,
            or simulate custom seat allocation levers in accordance with established workforce transition methodology.
            <em> Sanctioned training seats do not equal immediate qualified supply</em>.
            Transition yield: <code>Scenario Entrants = Additional Seats × Enrolment Rate × Completion Rate × Local Entry Rate</code>.
          </p>
        </div>
      </div>

      {/* Decision Intelligence: Policy Recommendations Shelf */}
      <div className="editorial-card" style={{ padding: '16px 20px', borderLeft: '4px solid #0f766e' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Compass size={18} style={{ color: '#0f766e' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#0f172a' }}>
              Evidence-Based Policy &amp; Workforce Recommendations
            </h3>
            <span style={{ fontSize: '11px', background: '#f0fdfa', color: '#0f766e', border: '1px solid #99f6e4', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
              {filteredRecs.length} Active
            </span>
          </div>

          {/* Archetype Filters */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {[
              { id: 'ALL', label: 'All Recommendations' },
              { id: 'TRAINING_CAPACITY_EXPANSION', label: 'Seat Expansion' },
              { id: 'CURRICULUM_MODERNIZATION_OR_PIVOT', label: 'Curriculum Pivot' },
              { id: 'APPRENTICESHIP_INDUSTRY_TIE_UP', label: 'Apprenticeships' },
              { id: 'DATA_COLLECTION_AUDIT', label: 'Data Audits' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setSelectedRecFilter(f.id)}
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '4px 10px',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  border: selectedRecFilter === f.id ? '1px solid #0f766e' : '1px solid #e2e8f0',
                  background: selectedRecFilter === f.id ? '#0f766e' : '#ffffff',
                  color: selectedRecFilter === f.id ? '#ffffff' : '#475569',
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {isRecsLoading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '12.5px' }}>
            Evaluating evidence and generating policy recommendations...
          </div>
        ) : filteredRecs.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '12.5px', background: '#f8fafc', borderRadius: '4px' }}>
            No recommendations match current filter criteria.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '12px' }}>
            {filteredRecs.map((rec) => {
              const isExpansion = rec.recommendation_type === 'TRAINING_CAPACITY_EXPANSION';
              const isPivot = rec.recommendation_type === 'CURRICULUM_MODERNIZATION_OR_PIVOT';
              const isApp = rec.recommendation_type === 'APPRENTICESHIP_INDUSTRY_TIE_UP';
              const isAudit = rec.recommendation_type === 'DATA_COLLECTION_AUDIT';

              const badgeColor = isExpansion
                ? { bg: '#eff6ff', border: '#bfdbfe', text: '#1d4ed8' }
                : isPivot
                ? { bg: '#fef3c7', border: '#fde68a', text: '#b45309' }
                : isApp
                ? { bg: '#f0fdf4', border: '#bbf7d0', text: '#15803d' }
                : { bg: '#fef2f2', border: '#fecaca', text: '#b91c1c' };

              const Icon = isExpansion ? TrendingUp : isPivot ? BookOpen : isApp ? Building : FileSearch;

              return (
                <div
                  key={rec.recommendation_id}
                  style={{
                    border: '1px solid #e2e8f0',
                    borderRadius: '4px',
                    padding: '12px 14px',
                    background: '#ffffff',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px',
                  }}
                >
                  <div>
                    {/* Header Row */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          background: badgeColor.bg,
                          color: badgeColor.text,
                          border: `1px solid ${badgeColor.border}`,
                          padding: '2px 6px',
                          borderRadius: '3px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <Icon size={11} />
                        {rec.recommendation_type.replace(/_/g, ' ')}
                      </span>

                      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                        <span
                          style={{
                            fontSize: '9.5px',
                            fontWeight: 700,
                            padding: '1px 5px',
                            borderRadius: '3px',
                            background: rec.priority === 'HIGH' ? '#fee2e2' : '#fef9c3',
                            color: rec.priority === 'HIGH' ? '#991b1b' : '#854d0e',
                          }}
                        >
                          {rec.priority} PRIORITY
                        </span>
                        <span
                          style={{
                            fontSize: '9.5px',
                            fontWeight: 600,
                            padding: '1px 5px',
                            borderRadius: '3px',
                            background: '#f1f5f9',
                            color: '#475569',
                          }}
                        >
                          {rec.district_code}
                        </span>
                      </div>
                    </div>

                    {/* Title & Target */}
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', marginBottom: '4px', lineHeight: 1.3 }}>
                      {rec.action_title}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>
                      Target: <strong>{rec.canonical_title || rec.nco_code}</strong> | Horizon: {rec.target_horizon_months} Months
                    </div>

                    {/* Rationale */}
                    <p style={{ fontSize: '11.5px', color: '#334155', margin: '0 0 8px 0', lineHeight: 1.45 }}>
                      {rec.rationale}
                    </p>

                    {/* Expected Impact */}
                    <div style={{ fontSize: '11px', background: '#f8fafc', padding: '6px 8px', borderRadius: '3px', border: '1px solid #e2e8f0', color: '#0f766e', fontWeight: 500 }}>
                      <strong>Impact:</strong> {rec.expected_impact_summary}
                    </div>
                  </div>

                  {/* Footer Action */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '8px' }}>
                    <span style={{ fontSize: '10.5px', color: '#64748b' }}>
                      Feasibility: <strong>{(rec.feasibility_score * 100).toFixed(0)}%</strong>
                    </span>

                    {rec.proposed_seat_adjustment > 0 ? (
                      <button
                        onClick={() => handleApplyRecommendation(rec)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          background: '#0f766e',
                          color: '#ffffff',
                          border: 'none',
                          padding: '4px 10px',
                          borderRadius: '3px',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <span>Simulate {rec.proposed_seat_adjustment} Seats</span>
                        <ArrowRight size={12} />
                      </button>
                    ) : (
                      <span style={{ fontSize: '10.5px', color: '#64748b', fontStyle: 'italic' }}>
                        {isAudit ? 'Survey Advisory' : 'Curriculum Audit'}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Target Trade Selection Strip */}
      <div
        id="scenario-simulator-levers"
        style={{
          background: '#ffffff',
          border: '1px solid #e7e5e4',
          borderRadius: '4px',
          padding: '12px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label htmlFor="scenario-trade-picker" style={{ fontSize: '12.5px', fontWeight: 700, color: '#1c1917' }}>
            Target Occupation:
          </label>
          <select
            id="scenario-trade-picker"
            value={selectedOccId}
            onChange={(e) => {
              setSelectedOccId(e.target.value);
              setParams((p) => ({ ...p, targetOccupationId: e.target.value }));
            }}
            style={{
              padding: '5px 10px',
              borderRadius: '3px',
              border: '1px solid #d6d3d1',
              fontSize: '12.5px',
              fontWeight: 600,
              color: '#1c1917',
              backgroundColor: '#ffffff',
            }}
            aria-label="Select Target Occupation for Scenario"
          >
            {filteredTradeOptions.map((t) => (
              <option key={t.id} value={t.id}>
                {t.canonicalTitle} ({t.district}) — Baseline Gap: {formatSignedNumber(t.baselineGap)}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() =>
              setParams({
                targetOccupationId: activeTrade?.id || 'occ-solar-pune',
                proposedSeats: 350,
                enrolmentRate: 90,
                completionRate: 85,
                localEntryRate: 70,
                trainerRatioRequired: 20,
                unitCostPerSeat: 18500,
              })
            }
            className="action-link"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              border: '1px solid #d6d3d1',
              padding: '4px 10px',
              borderRadius: '3px',
              fontSize: '12px',
              cursor: 'pointer',
              background: '#ffffff',
            }}
          >
            <RotateCcw size={12} /> Reset to Defaults
          </button>
        </div>
      </div>

      {/* Main 2-Column Working Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1fr) minmax(420px, 1.4fr)', gap: '16px' }}>
        {/* Left Column: Input Levers */}
        <div className="editorial-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="editorial-card-header" style={{ marginBottom: 0, paddingBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sliders size={14} style={{ color: '#c2410c' }} />
              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#1c1917' }}>Sanction Levers &amp; Conversion Rates</h4>
            </div>
          </div>

          {/* Lever 1: Proposed Seat Expansion */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, color: '#44403c' }}>Proposed Additional Sanctioned Seats:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#c2410c' }}>
                +{formatNumber(params.proposedSeats)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1500"
              step="50"
              value={params.proposedSeats}
              onChange={(e) => setParams({ ...params, proposedSeats: Number(e.target.value) })}
              style={{ width: '100%', cursor: 'pointer', accentColor: '#c2410c' }}
              aria-label="Proposed Additional Seats Slider"
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#a8a29e' }}>
              <span>0 (Status Quo)</span>
              <span>750</span>
              <span>1,500 Max</span>
            </div>
          </div>

          {/* Lever 2: Enrolment Take-Up Rate */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, color: '#44403c' }}>Enrolment Take-Up Rate:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{params.enrolmentRate}%</span>
            </div>
            <input
              type="range"
              min="50"
              max="100"
              value={params.enrolmentRate}
              onChange={(e) => setParams({ ...params, enrolmentRate: Number(e.target.value) })}
              style={{ width: '100%', cursor: 'pointer', accentColor: '#c2410c' }}
              aria-label="Enrolment Rate Slider"
            />
          </div>

          {/* Lever 3: Completion & Certification Rate */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, color: '#44403c' }}>Course Completion &amp; Certification:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{params.completionRate}%</span>
            </div>
            <input
              type="range"
              min="40"
              max="100"
              value={params.completionRate}
              onChange={(e) => setParams({ ...params, completionRate: Number(e.target.value) })}
              style={{ width: '100%', cursor: 'pointer', accentColor: '#c2410c' }}
              aria-label="Completion Rate Slider"
            />
          </div>

          {/* Lever 4: Target Role Entry Rate */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, color: '#44403c' }}>Target Role &amp; District Retention:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{params.localEntryRate}%</span>
            </div>
            <input
              type="range"
              min="30"
              max="100"
              value={params.localEntryRate}
              onChange={(e) => setParams({ ...params, localEntryRate: Number(e.target.value) })}
              style={{ width: '100%', cursor: 'pointer', accentColor: '#c2410c' }}
              aria-label="Local Role Entry Rate Slider"
            />
          </div>

          {/* Step-by-Step Calculation Breakdown */}
          {backendResult && backendResult.calculation_steps && (
            <div
              style={{
                marginTop: '10px',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '4px',
                padding: '10px 12px',
                fontSize: '11px',
                color: '#334155',
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Cpu size={12} style={{ color: '#0f766e' }} />
                <span>Backend Arithmetic Audit Trail (Master R&amp;D Sec. 10)</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: '16px', lineHeight: 1.5 }}>
                {backendResult.calculation_steps.map((step, sIdx) => (
                  <li key={sIdx}>{step}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right Column: Outcomes & Before/After Visual */}
        <div className="editorial-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="editorial-card-header" style={{ marginBottom: 0, paddingBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Building size={14} style={{ color: '#1e3a8a' }} />
              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#1c1917' }}>Projected Labour Market Impact</h4>
            </div>
          </div>

          {/* Metric Ledger Mini-strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
            <div style={{ background: '#fcfaf6', padding: '10px 12px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
              <span style={{ fontSize: '10.5px', color: '#78716c', textTransform: 'uppercase', fontWeight: 600 }}>
                Effective Yield / Seat
              </span>
              <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'monospace', color: '#1c1917' }}>
                {(yieldPerSeat * 100).toFixed(1)}%
              </div>
              <span style={{ fontSize: '10px', color: '#a8a29e' }}>enrol × complete × enter</span>
            </div>

            <div style={{ background: '#f0fdfa', padding: '10px 12px', borderRadius: '4px', border: '1px solid #99f6e4' }}>
              <span style={{ fontSize: '10.5px', color: '#0f766e', textTransform: 'uppercase', fontWeight: 600 }}>
                Expected Entrants
              </span>
              <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'monospace', color: '#0d9488' }}>
                +{formatNumber(expectedQualifiedEntrants)}
              </div>
              <span style={{ fontSize: '10px', color: '#0f766e' }}>Available qualified pool</span>
            </div>
          </div>

          {/* Gap Progression Chart */}
          <div style={{ border: '1px solid #e7e5e4', borderRadius: '4px', padding: '10px', background: '#fafaf9' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#78716c', marginBottom: '8px' }}>
              Gap Closure Trajectory (Pre vs. Post Transition):
            </div>
            <div style={{ height: '140px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparisonChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value) => [`${value} workers`, 'Volume']} />
                  <Bar dataKey="workers" radius={[3, 3, 0, 0]}>
                    {comparisonChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Residual Gap Callout */}
          <div
            style={{
              background: residualGap <= 0 ? '#f0fdf4' : '#fff7ed',
              border: `1px solid ${residualGap <= 0 ? '#86efac' : '#fed7aa'}`,
              borderRadius: '4px',
              padding: '10px 14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ fontWeight: 700, fontSize: '13px', color: '#1c1917' }}>
                Projected Residual Gap:
              </span>
              <span
                style={{
                  fontFamily: 'monospace',
                  fontSize: '18px',
                  fontWeight: 700,
                  color: residualGap <= 0 ? '#15803d' : '#c2410c',
                }}
              >
                {formatSignedNumber(residualGap)}
              </span>
            </div>
            <div style={{ fontSize: '11.5px', marginTop: '3px', color: '#57534e' }}>
              {residualGap <= 0
                ? `Projected shortage closed (${gapReductionPercent}% reduction).`
                : `Projected shortage reduced by ${gapReductionPercent}%. Residual shortage of ${residualGap} workers.`}
            </div>
          </div>

          {/* Operational Feasibility Box */}
          <div style={{ background: '#f5f5f4', padding: '10px 12px', borderRadius: '4px', border: '1px solid #e7e5e4', fontSize: '11.5px' }}>
            <div style={{ fontWeight: 700, color: '#1c1917', marginBottom: '3px' }}>
              Operational Requirements:
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#57534e' }}>
              <span>Certified Trainers Needed:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{instructorsNeeded} instructors (1:20 ratio)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#57534e' }}>
              <span>Estimated Budget:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>₹{formatNumber(estimatedBudget)} (@ ₹18,500/seat)</span>
            </div>
          </div>

          {fallbackResult.feasibilityWarning && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', background: '#fffbeb', border: '1px solid #fde68a', padding: '8px 10px', borderRadius: '4px', fontSize: '11px', color: '#92400e' }}>
              <AlertCircle size={13} style={{ marginTop: '2px', flexShrink: 0 }} />
              <span>{fallbackResult.feasibilityWarning}</span>
            </div>
          )}

          <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '10.5px', color: '#78716c', borderTop: '1px solid #e7e5e4', paddingTop: '8px' }}>
            <ShieldCheck size={13} style={{ color: '#0f766e', marginTop: '2px', flexShrink: 0 }} />
            <span>
              <strong>Decision-Support Notice:</strong> Scenarios evaluate potential outcomes under stated assumptions. 
              Seat allocations require District Skill Committee sign-off, facility audit, and budgetary approval.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
