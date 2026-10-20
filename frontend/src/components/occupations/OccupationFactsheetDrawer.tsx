import React from 'react';
import { X, CheckCircle2, AlertTriangle, Layers, Clock } from 'lucide-react';
import type { OccupationSummary } from '../../types/lmis';
import { formatNumber, formatSignedNumber, formatGapRate } from '../../utils/calculations';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

interface OccupationFactsheetDrawerProps {
  occupation: OccupationSummary | null;
  onClose: () => void;
}

export const OccupationFactsheetDrawer: React.FC<OccupationFactsheetDrawerProps> = ({
  occupation,
  onClose,
}) => {
  if (!occupation) return null;

  const isShortage = occupation.absoluteGap > 0;
  const isSurplus = occupation.absoluteGap < 0;

  return (
    <>
      <div
        className="factsheet-drawer-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className="factsheet-drawer"
        role="dialog"
        aria-label={`Occupation Factsheet: ${occupation.canonicalTitle}`}
      >
        <div className="drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <span className="data-status-tag" style={{ fontSize: '9.5px', padding: '1px 5px' }}>
                {occupation.sourceStatus === 'IMPORTED' ? 'VERIFIED IMPORT' : 'SYNTHETIC BASELINE'}
              </span>
              <span style={{ fontSize: '11px', fontFamily: 'monospace', color: '#78716c' }}>
                NCO: {occupation.ncoCode}
              </span>
              <span style={{ fontSize: '10.5px', background: '#eff6ff', color: '#1e3a8a', padding: '1px 5px', borderRadius: '2px', fontWeight: 600 }}>
                NSQF L{occupation.nsqfLevel}
              </span>
            </div>
            <h3>{occupation.canonicalTitle}</h3>
            <div style={{ fontSize: '12px', color: '#57534e', marginTop: '2px' }}>
              {occupation.sector} · District: <strong>{occupation.district}</strong>
            </div>
          </div>
          <button
            type="button"
            className="gov-btn gov-btn-outline"
            style={{ padding: '4px 6px' }}
            onClick={onClose}
            aria-label="Close factsheet drawer"
          >
            <X size={15} />
          </button>
        </div>

        <div className="drawer-body">
          {/* Projected Gap Callout */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '4px',
              background: isShortage ? '#fff7ed' : isSurplus ? '#eef2ff' : '#f0fdf4',
              border: `1px solid ${isShortage ? '#fed7aa' : isSurplus ? '#c7d2fe' : '#bbf7d0'}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#44403c' }}>Projected Labour Gap:</span>
              <span
                style={{
                  fontFamily: 'monospace',
                  fontWeight: 700,
                  fontSize: '18px',
                  color: isShortage ? '#c2410c' : isSurplus ? '#4338ca' : '#15803d',
                }}
              >
                {formatSignedNumber(occupation.absoluteGap)} ({formatGapRate(occupation.gapRate)})
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '11.5px', color: '#57534e' }}>
              <span>Documented Demand: <strong>{formatNumber(occupation.documentedDemand)}</strong></span>
              <span>Qualified Supply: <strong>{formatNumber(occupation.qualifiedSupply)}</strong></span>
            </div>
          </div>

          {/* Historical Demand Trend (Recharts micro-chart) */}
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#78716c', letterSpacing: '0.05em', marginBottom: '6px' }}>
              12-Month Demand Signal Trajectory
            </div>
            <div style={{ width: '100%', height: 130, background: '#fcfaf6', padding: '8px 8px 4px 0', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={occupation.monthlyHistory}>
                  <XAxis dataKey="period" tick={{ fontSize: 9, fill: '#78716c' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: '#78716c' }} tickLine={false} axisLine={false} domain={['dataMin - 50', 'dataMax + 50']} />
                  <Tooltip
                    contentStyle={{ fontSize: '11px', padding: '4px 8px', borderRadius: '3px' }}
                    formatter={(val) => [`${val} postings`, 'Demand Signal']}
                  />
                  <Line type="monotone" dataKey="demand" stroke="#1e3a8a" strokeWidth={2} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Taxonomic Hierarchy */}
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#78716c', letterSpacing: '0.05em', marginBottom: '6px' }}>
              NCO-2015 Classification Hierarchy
            </div>
            <div style={{ background: '#fcfaf6', border: '1px solid #e7e5e4', borderRadius: '4px', padding: '10px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11.5px', color: '#292524', marginBottom: '4px' }}>
                <Layers size={13} style={{ color: '#0f766e' }} />
                <span><strong>Division:</strong> {occupation.ncoDivision}</span>
              </div>
              <p style={{ fontSize: '11.5px', color: '#57534e', lineHeight: 1.45 }}>
                {occupation.taskDescription}
              </p>
            </div>
          </div>

          {/* Training Pipeline Funnel */}
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#78716c', letterSpacing: '0.05em', marginBottom: '6px' }}>
              Institutional Training Pipeline Funnel
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#fcfaf6', border: '1px solid #e7e5e4', borderRadius: '3px', fontSize: '12px' }}>
                <span style={{ color: '#44403c' }}>Sanctioned Annual Training Seats</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{formatNumber(occupation.trainingCapacity)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#fcfaf6', border: '1px solid #e7e5e4', borderRadius: '3px', fontSize: '12px' }}>
                <span style={{ color: '#44403c' }}>Enrolled Trainees</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{formatNumber(occupation.enrolledStudents)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#fcfaf6', border: '1px solid #e7e5e4', borderRadius: '3px', fontSize: '12px' }}>
                <span style={{ color: '#44403c' }}>Certified Course Completers</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{formatNumber(occupation.certifiedWorkers)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#f0fdfa', border: '1px solid #99f6e4', borderRadius: '3px', fontSize: '12px' }}>
                <span style={{ color: '#0f766e', fontWeight: 600 }}>Reported Placement Tracking Rate</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#0f766e' }}>{occupation.reportedPlacementRate}%</span>
              </div>
            </div>
            <div style={{ fontSize: '10.5px', color: '#78716c', fontStyle: 'italic', marginTop: '3px' }}>
              * Methodological Guardrail: Sanctioned seats and certifications measure institutional throughput, not active labour supply.
            </div>
          </div>

          {/* Recognized Title Aliases */}
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#78716c', letterSpacing: '0.05em', marginBottom: '6px' }}>
              Standardized Title Aliases (Normalized)
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
              {occupation.aliases.map((alias, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: '11px',
                    padding: '2px 7px',
                    background: '#f5f5f4',
                    borderRadius: '3px',
                    border: '1px solid #d6d3d1',
                    color: '#44403c',
                  }}
                >
                  &quot;{alias}&quot;
                </span>
              ))}
            </div>
          </div>

          {/* Caveat and Uncertainty Notice */}
          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '4px', padding: '10px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#92400e', fontSize: '11.5px', fontWeight: 700, marginBottom: '3px' }}>
              <AlertTriangle size={13} />
              <span>Evidence Caveats &amp; Limitations</span>
            </div>
            <p style={{ fontSize: '11px', color: '#78350f', lineHeight: 1.45 }}>
              {occupation.caveat}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10.5px', color: '#78716c', borderTop: '1px solid #e7e5e4', paddingTop: '8px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={11} style={{ color: '#0f766e' }} /> Mapping Confidence: {occupation.mappingConfidence}%
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={11} /> Snapshot: {occupation.lastUpdated}
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
