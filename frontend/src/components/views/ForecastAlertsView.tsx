import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  ShieldAlert,
  GitCommit,
  CheckCircle2,
  HelpCircle,
  FileCheck,
  Send,
  RefreshCw,
} from 'lucide-react';
import { SYNTHETIC_OCCUPATIONS, SYNTHETIC_ALERTS } from '../../data/syntheticData';
import {
  evaluateChronologicalHoldout,
  formatSignedNumber,
  formatGapRate,
} from '../../utils/calculations';
import type { PilotDistrict, EarlyWarningSignal, ForecastModelEvaluation, DataStatusLabel, AlertType } from '../../types/lmis';
import { apiClient } from '../../services/apiClient';
import type { BackendForecastResponse, BackendAlertItem } from '../../services/apiClient';

interface ForecastAlertsViewProps {
  selectedDistrict: PilotDistrict;
  selectedSector?: string;
}

interface TradeOption {
  id: string;
  ncoCode: string;
  canonicalTitle: string;
  district: string;
  districtCode: string;
  dataStatus?: string;
}

export const ForecastAlertsView: React.FC<ForecastAlertsViewProps> = ({
  selectedDistrict,
}) => {
  const [tradeOptions, setTradeOptions] = useState<TradeOption[]>(() =>
    SYNTHETIC_OCCUPATIONS.map((occ) => ({
      id: occ.id,
      ncoCode: occ.ncoCode,
      canonicalTitle: occ.canonicalTitle,
      district: occ.district,
      districtCode: occ.district === 'Pune' ? 'MH_PUN' : 'MH_NSK',
      dataStatus: occ.sourceStatus,
    }))
  );
  const [selectedOccId, setSelectedOccId] = useState<string>('occ-solar-pune');
  const [alertsState, setAlertsState] = useState<EarlyWarningSignal[]>(SYNTHETIC_ALERTS);
  const [selectedAlertTypeFilter, setSelectedAlertTypeFilter] = useState<string>('ALL');
  const [backendForecast, setBackendForecast] = useState<BackendForecastResponse | null>(null);
  const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);
  const [isForecastLoading, setIsForecastLoading] = useState<boolean>(false);

  // Load dynamic occupations from backend gap intelligence
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
          dataStatus: g.data_status || 'SYNTHETIC_DEMO',
        }));
        setTradeOptions(options);
        setSelectedOccId((prev) => (options.some((o) => o.id === prev) ? prev : options[0].id));
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  const selectedTrade = tradeOptions.find((t) => t.id === selectedOccId) || tradeOptions[0];
  const ncoCode = selectedTrade ? selectedTrade.ncoCode : '7421.0301';
  const districtCode = selectedTrade ? selectedTrade.districtCode : 'MH_PUN';
  const displayTitle = selectedTrade ? selectedTrade.canonicalTitle : 'Solar PV Installer';

  const syntheticMatch = SYNTHETIC_OCCUPATIONS.find((o) => o.ncoCode === ncoCode) || SYNTHETIC_OCCUPATIONS[0];
  const historicalNumbers = syntheticMatch.monthlyHistory.map((h) => h.demand);

  // Manual re-evaluate action
  const handleManualReevaluate = async () => {
    setIsForecastLoading(true);
    try {
      const fcst = await apiClient.getProjections(ncoCode, districtCode, 'DEMAND', 3);
      setBackendForecast(fcst);
      setIsLiveBackend(true);

      const backendAlerts = await apiClient.getAlerts(selectedDistrict);
      if (backendAlerts && backendAlerts.length > 0) {
        setAlertsState(
          backendAlerts.map((a: BackendAlertItem) => ({
            id: a.alert_id,
            alertType: (a.alert_type === 'DATA_QUALITY_WARNING' ? 'DATA_WARNING' : a.alert_type) as AlertType,
            severity: a.severity === 'CRITICAL' ? 'HIGH' : a.severity === 'WARNING' ? 'MEDIUM' : 'LOW',
            triageStatus: (a.triage_status || 'NEW') as EarlyWarningSignal['triageStatus'],
            triageNote: a.triage_note || undefined,
            occupation: a.canonical_title || `NCO ${a.nco_code}`,
            ncoCode: a.nco_code,
            district: a.district_code === 'MH_PUN' ? 'Pune' : a.district_code === 'MH_NSK' ? 'Nashik' : a.district_code,
            projectedGap: a.absolute_gap || 0,
            gapRate: a.gap_rate_pct,
            evidenceSummary: a.evidence_summary,
            uncertaintyNote: a.trigger_rule,
            recommendedAction: a.review_action_recommended,
            sourceStatus: (a.data_status === 'HYBRID_BASELINE_PLUS_IMPORT' ? 'IMPORTED' : a.data_status === 'IMPORTED' ? 'IMPORTED' : 'SYNTHETIC BASELINE') as DataStatusLabel,
            detectedAt: a.created_at ? a.created_at.split('T')[0] : '2026-10-18',
          }))
        );
      }
    } catch {
      setIsLiveBackend(false);
      setBackendForecast(null);
    } finally {
      setIsForecastLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getProjections(ncoCode, districtCode, 'DEMAND', 3)
      .then((fcst) => {
        if (!isMounted) return;
        setBackendForecast(fcst);
        setIsLiveBackend(true);
      })
      .catch(() => {
        if (!isMounted) return;
        setIsLiveBackend(false);
        setBackendForecast(null);
      });

    apiClient
      .getAlerts(selectedDistrict)
      .then((backendAlerts) => {
        if (!isMounted || !backendAlerts || backendAlerts.length === 0) return;
        setAlertsState(
          backendAlerts.map((a: BackendAlertItem) => ({
            id: a.alert_id,
            alertType: (a.alert_type === 'DATA_QUALITY_WARNING' ? 'DATA_WARNING' : a.alert_type) as AlertType,
            severity: a.severity === 'CRITICAL' ? 'HIGH' : a.severity === 'WARNING' ? 'MEDIUM' : 'LOW',
            triageStatus: (a.triage_status || 'NEW') as EarlyWarningSignal['triageStatus'],
            triageNote: a.triage_note || undefined,
            occupation: a.canonical_title || `NCO ${a.nco_code}`,
            ncoCode: a.nco_code,
            district: a.district_code === 'MH_PUN' ? 'Pune' : a.district_code === 'MH_NSK' ? 'Nashik' : a.district_code,
            projectedGap: a.absolute_gap || 0,
            gapRate: a.gap_rate_pct,
            evidenceSummary: a.evidence_summary,
            uncertaintyNote: a.trigger_rule,
            recommendedAction: a.review_action_recommended,
            sourceStatus: (a.data_status === 'HYBRID_BASELINE_PLUS_IMPORT' ? 'IMPORTED' : a.data_status === 'IMPORTED' ? 'IMPORTED' : 'SYNTHETIC BASELINE') as DataStatusLabel,
            detectedAt: a.created_at ? a.created_at.split('T')[0] : '2026-10-18',
          }))
        );
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, [selectedOccId, selectedDistrict, ncoCode, districtCode]);


  // Client-side fallback evaluation if backend offline
  const baselineMaEval: ForecastModelEvaluation = evaluateChronologicalHoldout(
    historicalNumbers,
    'BASELINE_MA',
    displayTitle,
    3
  );

  const naiveEval: ForecastModelEvaluation = evaluateChronologicalHoldout(
    historicalNumbers,
    'NAIVE_LAST',
    displayTitle,
    3
  );

  const driftEval: ForecastModelEvaluation = evaluateChronologicalHoldout(
    historicalNumbers,
    'LINEAR_DRIFT',
    displayTitle,
    3
  );

  const candidateEtsEval: ForecastModelEvaluation = evaluateChronologicalHoldout(
    historicalNumbers,
    'CANDIDATE_ETS',
    displayTitle,
    3
  );

  const candidateArimaEval: ForecastModelEvaluation = evaluateChronologicalHoldout(
    historicalNumbers,
    'CANDIDATE_ARIMA',
    displayTitle,
    3
  );

  // If backend is active and evaluated, overlay backend scorecard
  const evaluations: ForecastModelEvaluation[] = backendForecast && backendForecast.evaluation
    ? [
        {
          modelName: '3-Month Moving Average (Primary Baseline)',
          modelType: 'BASELINE_MA',
          targetSeries: displayTitle,
          evaluationStatus: backendForecast.evaluation.evaluation_status,
          holdoutPeriodsCount: backendForecast.evaluation.holdout_periods_count,
          calculatedMae: backendForecast.evaluation.baseline_mae,
          calculatedRmse: backendForecast.evaluation.baseline_rmse,
          calculatedMape: backendForecast.evaluation.baseline_mape,
          evaluationWindow: `${backendForecast.evaluation.train_start_period || '2025-05'} → ${backendForecast.evaluation.train_end_period || '2026-07'} (Train) | Held out 3M`,
          modelVerdict:
            backendForecast.evaluation.selected_model_name === 'MOVING_AVERAGE_3M'
              ? 'Selected Model (Baseline outperformed candidate on holdout)'
              : 'Benchmark reference model',
          modelSelectionVerdict:
            backendForecast.evaluation.selected_model_name === 'MOVING_AVERAGE_3M'
              ? 'Selected Model (Baseline outperformed candidate on holdout)'
              : 'Benchmark reference model',
          caveat: 'Holdout evaluation performed strictly without data leakage.',
        },
        {
          modelName: 'Holt Linear Exponential Smoothing (Candidate Model)',
          modelType: 'CANDIDATE_ETS',
          targetSeries: displayTitle,
          evaluationStatus: backendForecast.evaluation.evaluation_status,
          holdoutPeriodsCount: backendForecast.evaluation.holdout_periods_count,
          calculatedMae: backendForecast.evaluation.candidate_mae,
          calculatedRmse: backendForecast.evaluation.candidate_rmse,
          calculatedMape: backendForecast.evaluation.candidate_mape,
          evaluationWindow: `${backendForecast.evaluation.train_start_period || '2025-05'} → ${backendForecast.evaluation.train_end_period || '2026-07'} (Train) | Held out 3M`,
          modelVerdict: backendForecast.evaluation.model_comparison_verdict,
          modelSelectionVerdict: backendForecast.evaluation.model_comparison_verdict,
          caveat: 'Candidate model evaluated against moving average baseline.',
        },
        naiveEval,
        driftEval,
        candidateArimaEval,
      ]
    : [baselineMaEval, naiveEval, driftEval, candidateEtsEval, candidateArimaEval];

  const handleTriageAction = async (alertId: string, action: EarlyWarningSignal['triageStatus']) => {
    const today = new Date().toISOString().split('T')[0];
    const note = `Marked ${action} on ${today} by Planning Officer`;
    setAlertsState((prev) =>
      prev.map((alert) =>
        alert.id === alertId
          ? {
              ...alert,
              triageStatus: action,
              triageNote: note,
            }
          : alert
      )
    );
    try {
      await apiClient.updateAlertTriage(alertId, action, note, 'PLANNING_OFFICER');
    } catch {
      // Kept in optimistic local state
    }
  };

  const filteredAlerts = alertsState.filter((a) => {
    if (selectedDistrict !== 'All Districts' && a.district !== selectedDistrict) {
      return false;
    }
    if (selectedAlertTypeFilter !== 'ALL') {
      if (selectedAlertTypeFilter === 'DATA_WARNING') {
        if (a.alertType !== 'DATA_WARNING' && (a.alertType as string) !== 'DATA_QUALITY_WARNING') {
          return false;
        }
      } else if (a.alertType !== selectedAlertTypeFilter) {
        return false;
      }
    }
    return true;
  });

  return (
    <div className="editorial-viewport" role="main" aria-label="Forecast and Early-Warning Workspace">
      {/* Header Banner */}
      <div className="editorial-card">
        <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2>Demand-Supply Forecasting &amp; Early-Warning Intelligence</h2>
            <span className="data-status-tag" style={{ fontSize: '10px' }}>
              {isLiveBackend ? 'OPERATIONAL FORECAST ENGINE' : 'CALIBRATED BASELINE BENCHMARK'}
            </span>
          </div>
          <div className="heading-accent-bar"></div>
          <p>
            In accordance with <strong>LMIS analytical methodology (Section 9)</strong>, forecasting begins with transparent baselines 
            (Moving Average and Naïve last value). Candidate models (ETS / ARIMA) are evaluated on chronological holdout splits strictly prior to 
            test periods (zero future data leakage). <em>Evaluation metrics below are computed live from chronological observations.</em>
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginTop: '16px' }}>
          <div style={{ background: '#fcfaf6', padding: '12px 14px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
              <GitCommit size={13} style={{ color: '#0f766e' }} />
              <span>Evaluation Protocol</span>
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#1c1917', marginTop: '2px' }}>
              Chronological Holdout (3 Periods)
            </div>
            <div style={{ fontSize: '11px', color: '#78716c' }}>Zero future data leakage</div>
          </div>

          <div style={{ background: '#fcfaf6', padding: '12px 14px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
              <TrendingUp size={13} style={{ color: '#1e3a8a' }} />
              <span>Baseline Standard</span>
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#1c1917', marginTop: '2px' }}>
              3-Month Moving Average
            </div>
            <div style={{ fontSize: '11px', color: '#78716c' }}>Candidate must beat baseline MAE</div>
          </div>

          <div style={{ background: '#fcfaf6', padding: '12px 14px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
              <ShieldAlert size={13} style={{ color: '#c2410c' }} />
              <span>Integrity Guardrail</span>
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#1c1917', marginTop: '2px' }}>
              Never Fabricate Metrics
            </div>
            <div style={{ fontSize: '11px', color: '#78716c' }}>Unfitted models show 'Not evaluated'</div>
          </div>
        </div>
      </div>

      {/* Benchmark Scorecard */}
      <section className="editorial-card" aria-label="Model Benchmark Matrix">
        <div className="editorial-card-header">
          <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3>Chronological Holdout Benchmark Scorecard</h3>
              <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>
                {isLiveBackend ? 'OPERATIONAL SCORECARD' : 'EVALUATION BENCHMARK'}
              </span>
            </div>
            <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
            <p style={{ fontSize: '12px', marginTop: '4px' }}>
              Calculated error metrics (MAE, RMSE, MAPE) across models evaluated strictly on held-out observations.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              type="button"
              onClick={handleManualReevaluate}
              disabled={isForecastLoading}

              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'transparent',
                border: '1px solid #d6d3d1',
                padding: '4px 8px',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '11px',
                color: '#57534e',
              }}
              title="Re-run forecast holdout evaluation"
            >
              <RefreshCw size={11} className={isForecastLoading ? 'spin' : ''} />
              <span>{isForecastLoading ? 'Evaluating...' : 'Re-evaluate'}</span>
            </button>

            <div className="ribbon-filter">
              <label htmlFor="forecast-eval-select" style={{ fontSize: '11px' }}>Target Trade:</label>
              <select
                id="forecast-eval-select"
                value={selectedOccId}
                onChange={(e) => setSelectedOccId(e.target.value)}
                aria-label="Select Target Occupation for Model Evaluation"
              >
                {tradeOptions.map((occ) => (
                  <option key={occ.id} value={occ.id}>
                    {occ.canonicalTitle} ({occ.district}) — {occ.ncoCode}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Live Forecast Projections with Provenance & Uncertainty Bounds Banner */}
        {backendForecast && backendForecast.forecast_points && backendForecast.forecast_points.length > 0 && (
          <div
            style={{
              margin: '12px 0 16px',
              padding: '12px 16px',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '4px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
                  Forward 3-Month Demand Projections (Approximate 80% Uncertainty Intervals)
                </span>
                {backendForecast.data_status === 'HYBRID_BASELINE_PLUS_IMPORT' ? (
                  <span className="ledger-badge moderate" style={{ fontSize: '10px' }}>
                    HYBRID (BASELINE + RECONCILED IMPORT)
                  </span>
                ) : backendForecast.data_status === 'IMPORTED' ? (
                  <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>
                    IMPORTED RECONCILED POSTINGS
                  </span>
                ) : (
                  <span className="ledger-badge neutral" style={{ fontSize: '10px' }}>
                    SYNTHETIC BASELINE
                  </span>
                )}
              </div>
              <span className="ledger-badge neutral" style={{ fontSize: '10px' }}>
                Selected Model: {backendForecast.evaluation.selected_model_name}
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
              {backendForecast.forecast_points.map((pt) => (
                <div
                  key={pt.period}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #cbd5e1',
                    borderRadius: '4px',
                    padding: '8px 12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Period {pt.period} (Step +{pt.step_ahead})</div>
                    <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: '#f1f5f9', color: '#475569' }}>
                      {pt.data_status || backendForecast.data_status}
                    </span>
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', margin: '4px 0' }}>
                    {pt.forecast_value.toLocaleString()} <span style={{ fontSize: '11px', fontWeight: 400, color: '#64748b' }}>vacancies</span>
                  </div>
                  <div style={{ fontSize: '10.5px', color: '#475569' }}>
                    80% CI: [{pt.lower_bound} — {pt.upper_bound}]
                  </div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: '8px', fontSize: '10.5px', color: '#64748b', fontStyle: 'italic' }}>
              Note: Interval bounds represent approximate 80% nominal coverage under Gaussian error assumptions with analytical state-space variance expansion (Hyndman et al.). Truncated at zero.
            </div>
          </div>
        )}

        <div className="table-wrapper-refined">
          <table className="editorial-table">
            <thead>
              <tr>
                <th>Model Name &amp; Specification</th>
                <th>Evaluation Status</th>
                <th className="num-val">Calculated MAE</th>
                <th className="num-val">Calculated RMSE</th>
                <th className="num-val">Calculated MAPE</th>
                <th>Evaluation Window</th>
                <th>Model Selection Verdict</th>
              </tr>
            </thead>
            <tbody>
              {evaluations.map((evalItem, idx) => (
                <tr key={idx}>
                  <td>
                    <div style={{ fontWeight: 600, color: '#1c1917' }}>{evalItem.modelName}</div>
                    <div style={{ fontSize: '10.5px', color: '#78716c', fontFamily: 'monospace' }}>
                      {evalItem.modelType}
                    </div>
                  </td>
                  <td>
                    {evalItem.evaluationStatus === 'EVALUATED' ? (
                      <span className="ledger-badge balanced" style={{ fontSize: '10.5px' }}>
                        <CheckCircle2 size={11} style={{ display: 'inline', marginRight: 4 }} /> EVALUATED
                      </span>
                    ) : (
                      <span className="ledger-badge neutral" style={{ fontSize: '10.5px' }}>
                        <HelpCircle size={11} style={{ display: 'inline', marginRight: 4 }} /> NOT EVALUATED
                      </span>
                    )}
                  </td>
                  <td className="num-val bold" style={{ color: evalItem.calculatedMae ? '#1c1917' : '#a8a29e' }}>
                    {evalItem.calculatedMae !== null ? evalItem.calculatedMae.toFixed(1) : '—'}
                  </td>
                  <td className="num-val" style={{ color: evalItem.calculatedRmse ? '#1c1917' : '#a8a29e' }}>
                    {evalItem.calculatedRmse !== null ? evalItem.calculatedRmse.toFixed(1) : '—'}
                  </td>
                  <td className="num-val" style={{ color: evalItem.calculatedMape ? '#1c1917' : '#a8a29e' }}>
                    {evalItem.calculatedMape !== null ? `${evalItem.calculatedMape.toFixed(1)}%` : '—'}
                  </td>
                  <td style={{ fontSize: '11px', color: '#57534e' }}>{evalItem.evaluationWindow}</td>
                  <td>
                    <span
                      style={{
                        fontSize: '11px',
                        color: (evalItem.modelSelectionVerdict || evalItem.modelVerdict).includes('Selected') ? '#0f766e' : '#57534e',
                        fontWeight: (evalItem.modelSelectionVerdict || evalItem.modelVerdict).includes('Selected') ? 600 : 400,
                      }}
                    >
                      {evalItem.modelSelectionVerdict || evalItem.modelVerdict}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Early-Warning Inbox */}
      <section className="editorial-card" aria-label="Early-Warning Decision Inbox">
        <div className="editorial-card-header">
          <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3>Early-Warning Intelligence Inbox</h3>
              <span className="ledger-badge critical" style={{ fontSize: '10px' }}>
                {filteredAlerts.filter((a) => a.severity === 'HIGH').length} CRITICAL SIGNALS
              </span>
            </div>
            <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
            <p style={{ fontSize: '12px', marginTop: '4px' }}>
              Automated alerts triggered by projected imbalance thresholds. Triage status allows planners to escalate for target review.
            </p>
          </div>

          <div className="ribbon-filter">
            <label htmlFor="alert-type-filter" style={{ fontSize: '11px' }}>Filter Signal Type:</label>
            <select
              id="alert-type-filter"
              value={selectedAlertTypeFilter}
              onChange={(e) => setSelectedAlertTypeFilter(e.target.value)}
              aria-label="Filter Alerts by Signal Type"
            >
              <option value="ALL">All Alert Types</option>
              <option value="SHORTAGE_RISK">Observed Shortage Risks Only</option>
              <option value="PROJECTED_SHORTAGE_RISK">Projected Shortage Risks Only (Forecast)</option>
              <option value="OVERSUPPLY_RISK">Observed Oversupply Risks Only</option>
              <option value="PROJECTED_OVERSUPPLY_RISK">Projected Oversupply Risks Only (Forecast)</option>
              <option value="DATA_WARNING">Data Quality Warnings Only</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredAlerts.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: '#78716c', background: '#fcfaf6', borderRadius: '4px' }}>
              No active alerts matching the selected filters.
            </div>
          ) : (
            filteredAlerts.map((alert) => {
              const isProjected = alert.alertType === 'PROJECTED_SHORTAGE_RISK' || alert.alertType === 'PROJECTED_OVERSUPPLY_RISK';
              const isDataWarning = alert.alertType === 'DATA_WARNING' || (alert.alertType as string) === 'DATA_QUALITY_WARNING';
              const borderAccentColor = isProjected
                ? (alert.severity === 'HIGH' ? '#9333ea' : '#7c3aed')
                : (alert.severity === 'HIGH' ? '#b91c1c' : alert.severity === 'MEDIUM' ? '#c2410c' : '#0f766e');

              return (
                <div
                  key={alert.id}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #e7e5e4',
                    borderLeft: `4px solid ${borderAccentColor}`,
                    borderRadius: '4px',
                    padding: '14px 16px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                        {isProjected ? (
                          <span
                            style={{
                              fontSize: '9.5px',
                              fontWeight: 700,
                              padding: '2px 7px',
                              borderRadius: '3px',
                              background: '#f3e8ff',
                              color: '#6b21a8',
                              border: '1px solid #e9d5ff',
                              letterSpacing: '0.03em',
                            }}
                          >
                            🔮 FORWARD PROJECTION
                          </span>
                        ) : isDataWarning ? (
                          <span
                            style={{
                              fontSize: '9.5px',
                              fontWeight: 700,
                              padding: '2px 7px',
                              borderRadius: '3px',
                              background: '#fef3c7',
                              color: '#92400e',
                              border: '1px solid #fde68a',
                              letterSpacing: '0.03em',
                            }}
                          >
                            ⚠️ DATA ADVISORY
                          </span>
                        ) : (
                          <span
                            style={{
                              fontSize: '9.5px',
                              fontWeight: 700,
                              padding: '2px 7px',
                              borderRadius: '3px',
                              background: '#f1f5f9',
                              color: '#334155',
                              border: '1px solid #e2e8f0',
                              letterSpacing: '0.03em',
                            }}
                          >
                            📊 OBSERVED EVIDENCE
                          </span>
                        )}

                        <span
                          className={`ledger-badge ${
                            alert.severity === 'HIGH' ? 'critical' : alert.severity === 'MEDIUM' ? 'moderate' : 'balanced'
                          }`}
                          style={{ fontSize: '10px' }}
                        >
                          {alert.alertType} • {alert.severity}
                        </span>
                        <span style={{ fontSize: '11px', color: '#78716c' }}>Detected: {alert.detectedAt}</span>
                        <span style={{ fontSize: '11px', color: '#78716c' }}>• District: <strong>{alert.district}</strong></span>
                      </div>
                      <h4 style={{ fontSize: '14px', margin: '4px 0 2px', color: '#1c1917', fontWeight: 600 }}>
                        {alert.occupation}
                      </h4>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '11px', color: '#78716c' }}>
                        {isProjected ? 'Projected Horizon Gap' : 'Labour Market Gap'}
                      </div>
                      <div
                        style={{
                          fontSize: '15px',
                          fontWeight: 700,
                          color: alert.projectedGap > 0 ? '#b91c1c' : '#0f766e',
                        }}
                      >
                        {formatSignedNumber(alert.projectedGap)} ({formatGapRate(alert.gapRate)})
                      </div>
                    </div>
                  </div>

                <p style={{ fontSize: '12.5px', color: '#44403c', margin: '8px 0', lineHeight: 1.5 }}>
                  {alert.evidenceSummary}
                </p>

                <div
                  style={{
                    background: '#fcfaf6',
                    padding: '8px 12px',
                    borderRadius: '3px',
                    fontSize: '11.5px',
                    color: '#57534e',
                    border: '1px solid #f5f5f4',
                    margin: '8px 0',
                  }}
                >
                  <strong>Recommended Review Action:</strong> {alert.recommendedAction}
                  <div style={{ marginTop: '4px', fontSize: '11px', color: '#78716c' }}>
                    <strong>Trigger Criteria:</strong> {alert.uncertaintyNote.replace('Prototype default rule:', 'Configurable default rule:').replace('Prototype rule:', 'Evaluation rule:')}
                  </div>
                </div>

                {alert.triageNote && (
                  <div style={{ fontSize: '11px', color: '#0f766e', marginTop: '6px', fontWeight: 500 }}>
                    ✓ {alert.triageNote}
                  </div>
                )}

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '12px', paddingTop: '8px', borderTop: '1px solid #f5f5f4' }}>
                  <div style={{ fontSize: '11px', color: '#78716c' }}>
                    Current Triage Status: <strong>{alert.triageStatus}</strong>
                  </div>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {alert.triageStatus === 'NEW' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleTriageAction(alert.id, 'ACKNOWLEDGED')}
                          style={{
                            background: '#f5f5f4',
                            border: '1px solid #d6d3d1',
                            padding: '3px 8px',
                            borderRadius: '3px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            color: '#44403c',
                          }}
                        >
                          Acknowledge
                        </button>
                        <button
                          type="button"
                          onClick={() => handleTriageAction(alert.id, 'ESCALATED')}
                          style={{
                            background: '#c2410c',
                            border: 'none',
                            color: '#ffffff',
                            padding: '3px 8px',
                            borderRadius: '3px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '3px',
                          }}
                        >
                          <Send size={11} />
                          <span>Escalate for Target Review</span>
                        </button>
                      </>
                    )}
                    {alert.triageStatus !== 'NEW' && (
                      <span style={{ fontSize: '11px', color: '#0f766e', fontWeight: 500 }}>
                        <FileCheck size={12} style={{ display: 'inline', marginRight: 3 }} /> Action Logged
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
        </div>
      </section>
    </div>
  );
};
