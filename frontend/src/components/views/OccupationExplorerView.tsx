import React, { useState, useEffect } from 'react';
import { BookOpen, Layers, Check, X, Shield, RefreshCw, CheckCircle2 } from 'lucide-react';
import { SYNTHETIC_OCCUPATIONS } from '../../data/syntheticData';
import { OccupationBreakdownTable } from '../overview/OccupationBreakdownTable';
import type { PilotDistrict, OccupationSummary, DataStatusLabel, RiskLevel } from '../../types/lmis';
import { apiClient } from '../../services/apiClient';
import type { BackendReviewQueueItem, BackendGapIndicator } from '../../services/apiClient';

interface OccupationExplorerViewProps {
  selectedDistrict: PilotDistrict;
  selectedSector?: string;
}

interface RawMappingReviewItem {
  id: string | number;
  rawTitle: string;
  sourcePortal: string;
  suggestedCanonical: string;
  suggestedNco: string;
  confidence: number;
  matchMethod: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
}

const INITIAL_REVIEW_QUEUE: RawMappingReviewItem[] = [
  {
    id: 'rev-01',
    rawTitle: 'Solar PV Rooftop Lead Installer',
    sourcePortal: 'NCS Feed (Simulated)',
    suggestedCanonical: 'Solar PV Installation & Maintenance Technician',
    suggestedNco: '7421.0301',
    confidence: 98,
    matchMethod: 'EXACT_ALIAS',
    status: 'APPROVED',
  },
  {
    id: 'rev-02',
    rawTitle: 'CNC Mechanical Plant Service Fitter',
    sourcePortal: 'Industrial Job Board Scrape',
    suggestedCanonical: 'Industrial Machinery Maintenance Mechanic',
    suggestedNco: '7233.0100',
    confidence: 76,
    matchMethod: 'SEMANTIC_SUGGESTION',
    status: 'PENDING',
  },
  {
    id: 'rev-03',
    rawTitle: 'Junior Data Clerk / Back Office MIS',
    sourcePortal: 'District Portal Postings',
    suggestedCanonical: 'Information Technology Operations Assistant',
    suggestedNco: '3511.0101',
    confidence: 84,
    matchMethod: 'TOKEN_NORM',
    status: 'PENDING',
  },
];

export const OccupationExplorerView: React.FC<OccupationExplorerViewProps> = ({
  selectedDistrict,
  selectedSector = 'ALL',
}) => {
  const [occupations, setOccupations] = useState<OccupationSummary[]>(SYNTHETIC_OCCUPATIONS);
  const [reviewQueue, setReviewQueue] = useState<RawMappingReviewItem[]>(INITIAL_REVIEW_QUEUE);
  const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [isRecomputing, setIsRecomputing] = useState<boolean>(false);
  const [recomputeFeedback, setRecomputeFeedback] = useState<string | null>(null);

  const fetchLiveGaps = async () => {
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
      }
    } catch {
      // Keep existing
    }
  };

  const fetchBackendQueue = async () => {
    try {
      const items: BackendReviewQueueItem[] = await apiClient.getReviewQueue('PENDING');
      if (items && items.length > 0) {
        setReviewQueue(
          items.map((i) => ({
            id: i.id,
            rawTitle: i.raw_title,
            sourcePortal: i.source_system,
            suggestedCanonical: i.suggested_canonical_title || 'Pending Classification',
            suggestedNco: i.suggested_nco_code || 'Unmapped',
            confidence: Math.round(i.confidence_score * 100),
            matchMethod: i.match_method,
            status: i.review_status,
          }))
        );
        setIsLiveBackend(true);
      }
    } catch {
      setIsLiveBackend(false);
      // Keep baseline demo queue
    }
  };

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        const items = await apiClient.getReviewQueue('PENDING');
        if (isMounted && items && items.length > 0) {
          setReviewQueue(
            items.map((i) => ({
              id: i.id,
              rawTitle: i.raw_title,
              sourcePortal: i.source_system,
              suggestedCanonical: i.suggested_canonical_title || 'Pending Classification',
              suggestedNco: i.suggested_nco_code || 'Unmapped',
              confidence: Math.round(i.confidence_score * 100),
              matchMethod: i.match_method,
              status: i.review_status,
            }))
          );
          setIsLiveBackend(true);
        }
      } catch {
        if (isMounted) setIsLiveBackend(false);
      }

      try {
        const gaps = await apiClient.getGaps(selectedDistrict);
        if (isMounted && gaps && gaps.length > 0) {
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
        }
      } catch {
        // Keep existing
      }
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, [selectedDistrict]);

  const handleRecomputePipeline = async () => {
    setIsRecomputing(true);
    setRecomputeFeedback(null);
    try {
      const res = await apiClient.recomputePipeline();
      setRecomputeFeedback(
        `Pipeline Recomputed: Aggregated ${res.total_approved_postings_aggregated} confirmed vacancies across ${res.observations_created_or_updated} demand observation(s). Excluded ${res.unresolved_postings_excluded} unapproved postings and ${res.rejected_postings_excluded} rejected. Evaluated ${res.alerts_evaluated} early-warning alerts.`
      );
      await fetchLiveGaps();
      await fetchBackendQueue();
      setTimeout(() => setRecomputeFeedback(null), 9000);
    } catch (err: unknown) {
      setRecomputeFeedback(`Pipeline recomputation notice: ${err instanceof Error ? err.message : 'Operation complete'}`);
    } finally {
      setIsRecomputing(false);
    }
  };

  const handleApprove = async (id: string | number) => {
    if (typeof id === 'number' && isLiveBackend) {
      try {
        await apiClient.submitReviewDecision(id, 'APPROVED', 'Approved by UI planner review');
        setActionFeedback(`Item #${id} approved! Click "Publish to Gap Engine" to recompute demand indicators.`);
        setTimeout(() => setActionFeedback(null), 4000);
      } catch (err: unknown) {
        console.error(err);
      }
    }
    setReviewQueue((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: 'APPROVED' } : item))
    );
  };

  const handleReject = async (id: string | number) => {
    if (typeof id === 'number' && isLiveBackend) {
      try {
        await apiClient.submitReviewDecision(id, 'REJECTED', 'Rejected by UI planner review');
        setActionFeedback(`Item #${id} marked REJECTED (guaranteed exclusion from confirmed demand).`);
        setTimeout(() => setActionFeedback(null), 4000);
      } catch (err: unknown) {
        console.error(err);
      }
    }
    setReviewQueue((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: 'REJECTED' } : item))
    );
  };

  return (
    <div className="editorial-viewport" role="main" aria-label="Occupation Explorer and Taxonomy Workspace">
      {/* Module Heading Header Card */}
      <div className="editorial-card">
        <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2>Occupation Explorer &amp; Taxonomy Normalization</h2>
            <span className="data-status-tag" style={{ fontSize: '10px' }}>
              {isLiveBackend ? 'OPERATIONAL REVIEW QUEUE' : 'CALIBRATED BASELINE'}
            </span>
          </div>
          <div className="heading-accent-bar"></div>
          <p>
            Standardizing raw vacancy titles to the <strong>National Classification of Occupations (NCO-2015)</strong>.
            Exact verified aliases take precedence. Uncertain titles are directed to a human-in-the-loop review queue rather than silently auto-assigned.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginTop: '16px' }}>
          <div style={{ background: '#fcfaf6', padding: '12px 14px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
              <Layers size={13} style={{ color: '#0f766e' }} />
              <span>Reference Standard</span>
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#1c1917', marginTop: '2px' }}>
              DGE NCO-2015 (8-Digit)
            </div>
          </div>

          <div style={{ background: '#fcfaf6', padding: '12px 14px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
              <BookOpen size={13} style={{ color: '#1e3a8a' }} />
              <span>Qualification Alignment</span>
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#1c1917', marginTop: '2px' }}>
              NSQF Levels 4 &amp; 5 Focus
            </div>
          </div>

          <div style={{ background: '#fcfaf6', padding: '12px 14px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
              <Shield size={13} style={{ color: '#c2410c' }} />
              <span>Mapping Governance</span>
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#1c1917', marginTop: '2px' }}>
              Human Review for Ambiguity
            </div>
          </div>
        </div>
      </div>

      {actionFeedback && (
        <div
          style={{
            background: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#065f46',
            padding: '10px 14px',
            borderRadius: '4px',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '16px',
          }}
        >
          <CheckCircle2 size={16} />
          <span>{actionFeedback}</span>
        </div>
      )}

      {/* Main Occupation Analytical Table */}
      <OccupationBreakdownTable
        occupations={occupations}
        selectedDistrict={selectedDistrict}
        selectedSector={selectedSector}
        title="Monitored Canonical Occupations — Maharashtra Pilot Corridor"
        subtitle="Click any row to open the complete Occupation Factsheet, training pipeline funnel, and historical signal trajectory."
      />

      {/* Interactive Title Normalization Queue */}
      <section className="editorial-card" aria-label="Human-in-the-Loop Normalization Queue">
        <div className="editorial-card-header">
          <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3>Occupation Title Normalization &amp; Review Queue</h3>
              <span className="ledger-badge neutral" style={{ fontSize: '10px' }}>
                {isLiveBackend ? 'OPERATIONAL PIPELINE ACTIVE' : 'LOCAL BASELINE MODE'}
              </span>
            </div>
            <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
            <p style={{ fontSize: '12px', marginTop: '4px' }}>
              Review raw posting titles where semantic confidence is below threshold (&lt;85%) or requires human verification.
              Only approved postings contribute to confirmed demand observations.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={handleRecomputePipeline}
              disabled={isRecomputing}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: '#0f766e',
                color: '#ffffff',
                border: 'none',
                padding: '5px 11px',
                borderRadius: '3px',
                cursor: isRecomputing ? 'not-allowed' : 'pointer',
                fontSize: '11px',
                fontWeight: 600,
                opacity: isRecomputing ? 0.7 : 1,
              }}
              title="Aggregate approved postings into confirmed demand observations and refresh gap calculations and alerts"
            >
              <RefreshCw size={11} className={isRecomputing ? 'spin' : ''} />
              <span>{isRecomputing ? 'Recomputing Pipeline...' : 'Publish to Gap Engine'}</span>
            </button>
            <button
              type="button"
              onClick={fetchBackendQueue}
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
              title="Refresh queue from backend"
            >
              <RefreshCw size={11} />
              <span>Refresh Queue</span>
            </button>
            <span style={{ fontSize: '11px', color: '#78716c' }}>
              Pending Items: <strong>{reviewQueue.filter((q) => q.status === 'PENDING').length}</strong>
            </span>
          </div>
        </div>

        {recomputeFeedback && (
          <div
            style={{
              margin: '12px 0 6px 0',
              padding: '10px 14px',
              background: recomputeFeedback.includes('notice') || recomputeFeedback.includes('failed') ? '#fff7ed' : '#ecfdf5',
              border: `1px solid ${recomputeFeedback.includes('notice') || recomputeFeedback.includes('failed') ? '#fed7aa' : '#a7f3d0'}`,
              color: recomputeFeedback.includes('notice') || recomputeFeedback.includes('failed') ? '#c2410c' : '#065f46',
              borderRadius: '4px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <span>{recomputeFeedback}</span>
          </div>
        )}

        <div className="table-wrapper-refined">
          <table className="ledger-table" aria-label="Occupation Normalization Queue">
            <thead>
              <tr>
                <th scope="col">Raw Job Title</th>
                <th scope="col">Source System</th>
                <th scope="col">Suggested Canonical Match</th>
                <th scope="col">Proposed NCO-2015</th>
                <th scope="col">Confidence</th>
                <th scope="col">Match Method</th>
                <th scope="col">Status</th>
                <th scope="col" style={{ textAlign: 'center' }}>Review Action</th>
              </tr>
            </thead>
            <tbody>
              {reviewQueue.map((item) => (
                <tr key={item.id} className={item.status === 'APPROVED' ? 'row-approved' : item.status === 'REJECTED' ? 'row-rejected' : ''}>
                  <td style={{ fontWeight: 600, color: '#1c1917' }}>"{item.rawTitle}"</td>
                  <td style={{ fontSize: '11.5px', color: '#78716c' }}>{item.sourcePortal}</td>
                  <td>
                    <strong>{item.suggestedCanonical}</strong>
                  </td>
                  <td>
                    <code style={{ fontSize: '11.5px', background: '#f5f5f4', padding: '2px 5px', borderRadius: '3px' }}>
                      {item.suggestedNco}
                    </code>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <div
                        style={{
                          width: '45px',
                          height: '5px',
                          background: '#e7e5e4',
                          borderRadius: '2px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${item.confidence}%`,
                            height: '100%',
                            background: item.confidence >= 90 ? '#0f766e' : item.confidence >= 75 ? '#c2410c' : '#b91c1c',
                          }}
                        ></div>
                      </div>
                      <span style={{ fontSize: '11px', fontWeight: 600 }}>{item.confidence}%</span>
                    </div>
                  </td>
                  <td>
                    <span
                      className="ledger-badge neutral"
                      style={{
                        fontSize: '10px',
                        letterSpacing: '0.02em',
                      }}
                    >
                      {item.matchMethod}
                    </span>
                  </td>
                  <td>
                    {item.status === 'APPROVED' ? (
                      <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>
                        APPROVED
                      </span>
                    ) : item.status === 'REJECTED' ? (
                      <span className="ledger-badge critical" style={{ fontSize: '10px' }}>
                        REJECTED
                      </span>
                    ) : (
                      <span className="ledger-badge moderate" style={{ fontSize: '10px' }}>
                        PENDING
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {item.status === 'PENDING' ? (
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <button
                          type="button"
                          onClick={() => handleApprove(item.id)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '3px',
                            background: '#0f766e',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: '3px',
                            padding: '3px 8px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            fontWeight: 500,
                          }}
                          title="Confirm this occupation classification"
                        >
                          <Check size={12} />
                          <span>Approve</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleReject(item.id)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '3px',
                            background: '#ffffff',
                            color: '#b91c1c',
                            border: '1px solid #fca5a5',
                            borderRadius: '3px',
                            padding: '3px 8px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            fontWeight: 500,
                          }}
                          title="Reject and exclude from confirmed demand"
                        >
                          <X size={12} />
                          <span>Reject</span>
                        </button>
                      </div>
                    ) : (
                      <span style={{ fontSize: '11px', color: '#78716c', fontStyle: 'italic' }}>Reviewed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
