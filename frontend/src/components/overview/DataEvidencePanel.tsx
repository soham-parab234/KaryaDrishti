import React from 'react';
import { Database, AlertOctagon, Clock } from 'lucide-react';
import { DATA_SOURCES_PROVENANCE } from '../../data/syntheticData';
import type { DataStatusLabel } from '../../types/lmis';

export const DataEvidencePanel: React.FC = () => {
  const renderStatusBadge = (status: DataStatusLabel) => {
    switch (status) {
      case 'SYNTHETIC DEMO':
      case 'SYNTHETIC BASELINE':
        return <span className="data-status-tag" style={{ fontSize: '9.5px', padding: '2px 5px' }}>SYNTHETIC BASELINE</span>;
      case 'REAL PUBLIC DATA':
        return <span className="ledger-badge balanced" style={{ fontSize: '9.5px' }}>PUBLIC BENCHMARK</span>;
      case 'PLANNED':
        return <span className="ledger-badge neutral" style={{ fontSize: '9.5px' }}>PLANNED CONNECTOR</span>;
      case 'IMPORTED':
        return <span className="ledger-badge balanced" style={{ fontSize: '9.5px' }}>VERIFIED IMPORT</span>;
    }
  };

  return (
    <div className="editorial-card" aria-label="Data Evidence and Integrity Registry">
      <div className="editorial-card-header">
        <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3>Data Provenance &amp; Limitations</h3>
            <span className="ledger-badge balanced" style={{ fontSize: '10px' }}>AUDIT VERIFIABLE</span>
          </div>
          <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>
            Registry of active datasets, status classifications, and domain guardrails.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
          <Database size={13} style={{ color: '#0f766e' }} />
          <span>5 Source Families</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {DATA_SOURCES_PROVENANCE.map((src) => (
          <div key={src.id} style={{ border: '1px solid #e7e5e4', borderRadius: '4px', padding: '10px 12px', background: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
              <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#1c1917' }}>{src.dataFamily}</span>
              {renderStatusBadge(src.currentStatus)}
            </div>
            <div style={{ fontSize: '11.5px', color: '#57534e', marginBottom: '4px' }}>
              <span><strong>Reference:</strong> {src.referenceSource}</span> · 
              <span> <strong>Scope:</strong> {src.geographyScope}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '10.5px', color: '#78716c', marginBottom: '4px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                <Clock size={11} /> {src.updateFrequency}
              </span>
              <span><strong>Volume:</strong> {src.recordCount}</span>
            </div>
            <div style={{ fontSize: '10.5px', color: '#9a3412', background: '#fff7ed', padding: '4px 6px', borderRadius: '3px', border: '1px solid #fed7aa' }}>
              <strong>Guardrail:</strong> {src.limitationNotice}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '14px', borderTop: '1px solid #e7e5e4', paddingTop: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '11px', color: '#57534e' }}>
          <AlertOctagon size={14} style={{ color: '#c2410c', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Operational Data Integrity Guardrails:</strong>
            <ul style={{ paddingLeft: '14px', marginTop: '2px', lineHeight: '1.4' }}>
              <li>Never claim live government API integrations until end-to-end verified with live access.</li>
              <li>Registrations (e-Shram) do not indicate job readiness or current availability.</li>
              <li>Training seats are capacity; completion rates and local transitions must be applied.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
