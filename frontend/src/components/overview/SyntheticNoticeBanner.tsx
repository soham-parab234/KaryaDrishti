import React from 'react';
import { Info, ShieldCheck } from 'lucide-react';

export const SyntheticNoticeBanner: React.FC = () => {
  return (
    <div className="editorial-notice-strip" role="region" aria-label="Data Provenance and Governance Notice">
      <Info size={16} style={{ color: '#b45309', flexShrink: 0, marginTop: '2px' }} aria-hidden="true" />
      <div style={{ flex: 1 }}>
        <strong>DATA PROVENANCE &amp; METHODOLOGY NOTICE:</strong> Labour demand observations, qualified supply estimates, and baseline projections for the Maharashtra pilot corridor (Pune &amp; Nashik) reflect{' '}
        <strong>calibrated synthetic baseline data</strong> alongside verified imported employer postings.{' '}
        They do not constitute official published government census statistics. External public systems (NCS, e-Shram, PLFS, and Scheme MIS) represent planned architecture connectors.
        In accordance with institutional analytical standards: <em>institutional training capacity is strictly distinguished from active qualified workforce supply</em>, and{' '}
        <em>all policy adjustments require human-in-the-loop review</em>.
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#92400e', fontWeight: 600, fontSize: '11px', flexShrink: 0 }}>
        <ShieldCheck size={14} />
        <span>Verified Provenance</span>
      </div>
    </div>
  );
};
