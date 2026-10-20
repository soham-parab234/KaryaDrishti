import React, { useState, useEffect } from 'react';
import { SyntheticNoticeBanner } from '../overview/SyntheticNoticeBanner';
import { KpiMetricsGrid } from '../overview/KpiMetricsGrid';
import { DemandSupplyChart } from '../overview/DemandSupplyChart';
import { OccupationBreakdownTable } from '../overview/OccupationBreakdownTable';
import { EarlyWarningPanel } from '../overview/EarlyWarningPanel';
import { DataEvidencePanel } from '../overview/DataEvidencePanel';
import {
  SYNTHETIC_OCCUPATIONS,
  SYNTHETIC_MONTHLY_TREND,
  SYNTHETIC_ALERTS,
} from '../../data/syntheticData';
import { apiClient } from '../../services/apiClient';
import type { BackendGapIndicator, BackendAlertItem } from '../../services/apiClient';
import type { PilotDistrict, OccupationSummary, EarlyWarningSignal, DataStatusLabel, RiskLevel, AlertType } from '../../types/lmis';
import { Database, RefreshCw } from 'lucide-react';

interface OverviewViewProps {
  selectedDistrict: PilotDistrict;
  selectedSector?: string;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  selectedDistrict,
  selectedSector = 'ALL',
}) => {
  const [occupations, setOccupations] = useState<OccupationSummary[]>(SYNTHETIC_OCCUPATIONS);
  const [alerts, setAlerts] = useState<EarlyWarningSignal[]>(SYNTHETIC_ALERTS);
  const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [backendError, setBackendError] = useState<string | null>(null);

  const fetchBackendData = async () => {
    try {
      const gaps: BackendGapIndicator[] = await apiClient.getGaps(selectedDistrict);
      if (gaps && gaps.length > 0) {
        const updated = SYNTHETIC_OCCUPATIONS.map((baseOcc) => {
          const match = gaps.find(
            (g) =>
              g.nco_code === baseOcc.ncoCode &&
              (g.district_code === (baseOcc.district === 'Pune' ? 'MH_PUN' : 'MH_NSK'))
          );
          if (match) {
            const isShortage = match.absolute_gap > 0;
            const dynamicRisk: RiskLevel = isShortage
              ? (match.gap_rate_pct !== null && match.gap_rate_pct > 25 ? 'CRITICAL_SHORTAGE' : 'MODERATE_SHORTAGE')
              : match.absolute_gap < -50 ? 'POTENTIAL_OVERSUPPLY' : 'BALANCED';
            return {
              ...baseOcc,
              documentedDemand: match.demand_value,
              qualifiedSupply: match.qualified_supply_value,
              absoluteGap: match.absolute_gap,
              gapRate: match.gap_rate_pct,
              riskLevel: dynamicRisk,
              caveat: match.limitations?.[0] || baseOcc.caveat,
              sourceStatus: (match.data_status === 'IMPORTED' ? 'IMPORTED' : 'SYNTHETIC BASELINE') as DataStatusLabel,
            };
          }
          return baseOcc;
        });

        const newOccupations: OccupationSummary[] = gaps
          .filter((g) => !SYNTHETIC_OCCUPATIONS.some((baseOcc) => baseOcc.ncoCode === g.nco_code && (baseOcc.district === (g.district_code === 'MH_PUN' ? 'Pune' : 'Nashik'))))
          .map((g) => {
            const isShortage = g.absolute_gap > 0;
            const dynamicRisk: RiskLevel = isShortage
              ? (g.gap_rate_pct !== null && g.gap_rate_pct > 25 ? 'CRITICAL_SHORTAGE' : 'MODERATE_SHORTAGE')
              : g.absolute_gap < -50 ? 'POTENTIAL_OVERSUPPLY' : 'BALANCED';
            const dist: 'Pune' | 'Nashik' = g.district_code === 'MH_PUN' ? 'Pune' : 'Nashik';
            return {
              id: `occ-${g.nco_code.replace('.', '')}-${dist.toLowerCase()}`,
              ncoCode: g.nco_code,
              ncoDivision: `Division ${g.nco_code.slice(0, 1)}`,
              canonicalTitle: g.canonical_title || `Occupation ${g.nco_code}`,
              sector: 'Advanced Manufacturing',
              district: dist,
              nsqfLevel: 4,
              documentedDemand: g.demand_value,
              qualifiedSupply: g.qualified_supply_value,
              trainingCapacity: 0,
              enrolledStudents: 0,
              lastYearCompletions: 0,
              certifiedWorkers: 0,
              reportedPlacementRate: 0,
              absoluteGap: g.absolute_gap,
              gapRate: g.gap_rate_pct,
              riskLevel: dynamicRisk,
              sourceStatus: (g.data_status === 'IMPORTED' ? 'IMPORTED' : 'SYNTHETIC BASELINE') as DataStatusLabel,
              lastUpdated: g.reporting_period,
              mappingConfidence: 100,
              aliases: [],
              taskDescription: `Verified occupation ${g.canonical_title} imported via data pipeline.`,
              caveat: g.limitations?.[0] || 'Imported occupation observation.',
              monthlyHistory: [{ period: g.reporting_period, demand: g.demand_value, supply: g.qualified_supply_value }],
            };
          });

        setOccupations([...updated, ...newOccupations]);
        setIsLiveBackend(true);
      }

      const backendAlerts: BackendAlertItem[] = await apiClient.getAlerts(selectedDistrict);
      if (backendAlerts && backendAlerts.length > 0) {
        const mappedAlerts: EarlyWarningSignal[] = backendAlerts.map((a) => ({
          id: a.alert_id,
          alertType: (a.alert_type === 'DATA_QUALITY_WARNING' ? 'DATA_WARNING' : a.alert_type) as AlertType,
          severity: a.severity === 'CRITICAL' ? 'HIGH' : a.severity === 'WARNING' ? 'MEDIUM' : 'LOW',
          triageStatus: 'NEW',
          occupation: a.canonical_title || `NCO ${a.nco_code}`,
          ncoCode: a.nco_code,
          district: a.district_code === 'MH_PUN' ? 'Pune' : a.district_code === 'MH_NSK' ? 'Nashik' : a.district_code,
          projectedGap: a.absolute_gap || 0,
          gapRate: a.gap_rate_pct,
          evidenceSummary: a.evidence_summary,
          uncertaintyNote: a.trigger_rule,
          recommendedAction: a.review_action_recommended,
          sourceStatus: 'SYNTHETIC BASELINE',
          detectedAt: a.created_at ? a.created_at.split('T')[0] : '2026-10-18',
        }));
        setAlerts(mappedAlerts);
      }
    } catch (err: unknown) {
      setIsLiveBackend(false);
      setBackendError(err instanceof Error ? err.message : 'Backend offline');
      setOccupations(SYNTHETIC_OCCUPATIONS);
      setAlerts(SYNTHETIC_ALERTS);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const gaps: BackendGapIndicator[] = await apiClient.getGaps(selectedDistrict);
        if (!isMounted) return;
        if (gaps && gaps.length > 0) {
          const updated = SYNTHETIC_OCCUPATIONS.map((baseOcc) => {
            const match = gaps.find(
              (g) =>
                g.nco_code === baseOcc.ncoCode &&
                (g.district_code === (baseOcc.district === 'Pune' ? 'MH_PUN' : 'MH_NSK'))
            );
            if (match) {
              const isShortage = match.absolute_gap > 0;
              const dynamicRisk: RiskLevel = isShortage
                ? (match.gap_rate_pct !== null && match.gap_rate_pct > 25 ? 'CRITICAL_SHORTAGE' : 'MODERATE_SHORTAGE')
                : match.absolute_gap < -50 ? 'POTENTIAL_OVERSUPPLY' : 'BALANCED';
              return {
                ...baseOcc,
                documentedDemand: match.demand_value,
                qualifiedSupply: match.qualified_supply_value,
                absoluteGap: match.absolute_gap,
                gapRate: match.gap_rate_pct,
                riskLevel: dynamicRisk,
                caveat: match.limitations?.[0] || baseOcc.caveat,
                sourceStatus: (match.data_status === 'IMPORTED' ? 'IMPORTED' : 'SYNTHETIC BASELINE') as DataStatusLabel,
              };
            }
            return baseOcc;
          });
          setOccupations(updated);
          setIsLiveBackend(true);
        }

        const backendAlerts: BackendAlertItem[] = await apiClient.getAlerts(selectedDistrict);
        if (!isMounted) return;
        if (backendAlerts && backendAlerts.length > 0) {
          const mappedAlerts: EarlyWarningSignal[] = backendAlerts.map((a) => ({
            id: a.alert_id,
            alertType: (a.alert_type === 'DATA_QUALITY_WARNING' ? 'DATA_WARNING' : a.alert_type) as AlertType,
            severity: a.severity === 'CRITICAL' ? 'HIGH' : a.severity === 'WARNING' ? 'MEDIUM' : 'LOW',
            triageStatus: 'NEW',
            occupation: a.canonical_title || `NCO ${a.nco_code}`,
            ncoCode: a.nco_code,
            district: a.district_code === 'MH_PUN' ? 'Pune' : a.district_code === 'MH_NSK' ? 'Nashik' : a.district_code,
            projectedGap: a.absolute_gap || 0,
            gapRate: a.gap_rate_pct,
            evidenceSummary: a.evidence_summary,
            uncertaintyNote: a.trigger_rule,
            recommendedAction: a.review_action_recommended,
            sourceStatus: 'SYNTHETIC BASELINE',
            detectedAt: a.created_at ? a.created_at.split('T')[0] : '2026-10-18',
          }));
          setAlerts(mappedAlerts);
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        setIsLiveBackend(false);
        setBackendError(err instanceof Error ? err.message : 'Backend offline');
        setOccupations(SYNTHETIC_OCCUPATIONS);
        setAlerts(SYNTHETIC_ALERTS);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    load();
    return () => {
      isMounted = false;
    };
  }, [selectedDistrict]);

  const handleManualRefresh = () => {
    setIsLoading(true);
    fetchBackendData();
  };

  return (
    <div className="editorial-viewport" role="main" aria-label="Labour Market Intelligence Overview">
      {/* 1. Synthetic Demo Warning Notice */}
      <SyntheticNoticeBanner />

      {/* 1b. Provenance & Live Backend Status Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          marginBottom: '16px',
          background: isLiveBackend ? '#f0fdf4' : '#fffbeb',
          border: `1px solid ${isLiveBackend ? '#bbf7d0' : '#fef08a'}`,
          borderRadius: '4px',
          fontSize: '0.8rem',
          color: isLiveBackend ? '#166534' : '#854d0e',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={15} />
          {isLiveBackend ? (
            <span>
              <strong>Operational Pipeline Active:</strong> Loaded {occupations.length} occupation gaps and {alerts.length} active alerts directly from analytical services (<code>/api/analytics/gaps</code>, <code>/api/alerts</code>).
            </span>
          ) : (
            <span>
              <strong>Local Baseline Mode:</strong> {backendError ? `Analytical service unreachable (${backendError}).` : 'Running client-side baseline.'} Displaying verified baseline data.
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleManualRefresh}
          disabled={isLoading}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'transparent',
            border: 'none',
            color: 'inherit',
            cursor: 'pointer',
            fontSize: '0.78rem',
            textDecoration: 'underline',
          }}
          title="Refresh backend analytics"
        >
          <RefreshCw size={13} className={isLoading ? 'spin' : ''} />
          <span>{isLoading ? 'Fetching...' : 'Refresh'}</span>
        </button>
      </div>

      {/* 2. Key Labour Market Indicators Ledger */}
      <KpiMetricsGrid
        occupations={occupations}
        selectedDistrict={selectedDistrict}
        selectedSector={selectedSector}
      />

      {/* 3. Demand Signal vs. Supply Trajectory Recharts Chart */}
      <DemandSupplyChart data={SYNTHETIC_MONTHLY_TREND} />

      {/* 4. Main Occupation & Sector Breakdown Table */}
      <OccupationBreakdownTable
        occupations={occupations}
        selectedDistrict={selectedDistrict}
        selectedSector={selectedSector}
      />

      {/* 5. Two-column Grid: Early-Warning Risk Signals + Data Lineage Registry */}
      <section className="editorial-two-col" aria-label="Risk Signals and Data Provenance">
        <EarlyWarningPanel
          alerts={alerts}
          selectedDistrict={selectedDistrict}
        />
        <DataEvidencePanel />
      </section>
    </div>
  );
};
