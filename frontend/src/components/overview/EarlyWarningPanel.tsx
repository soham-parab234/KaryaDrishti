import React from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  HelpCircle,
  FileCheck,
} from 'lucide-react';
import type { EarlyWarningSignal, PilotDistrict } from '../../types/lmis';
import { formatSignedNumber, formatGapRate } from '../../utils/calculations';

interface EarlyWarningPanelProps {
  alerts: EarlyWarningSignal[];
  selectedDistrict: PilotDistrict;
}

export const EarlyWarningPanel: React.FC<EarlyWarningPanelProps> = ({
  alerts,
  selectedDistrict,
}) => {
  const filteredAlerts = selectedDistrict === 'All Districts'
    ? alerts
    : alerts.filter((a) => a.district === selectedDistrict);

  const getAlertIcon = (type: EarlyWarningSignal['alertType']) => {
    switch (type) {
      case 'SHORTAGE_RISK':
        return <ArrowUpRight size={15} style={{ color: '#c2410c' }} />;
      case 'OVERSUPPLY_RISK':
        return <ArrowDownRight size={15} style={{ color: '#4338ca' }} />;
      case 'EMERGING_DEMAND':
        return <Sparkles size={15} style={{ color: '#b45309' }} />;
      case 'DATA_WARNING':
        return <HelpCircle size={15} style={{ color: '#78716c' }} />;
    }
  };

  const getAlertTitle = (type: EarlyWarningSignal['alertType']) => {
    switch (type) {
      case 'SHORTAGE_RISK':
        return 'Projected Shortage Signal';
      case 'OVERSUPPLY_RISK':
        return 'Potential Oversupply Signal';
      case 'EMERGING_DEMAND':
        return 'Emerging Demand Acceleration';
      case 'DATA_WARNING':
        return 'Data Sparsity / Forecast Caveat';
    }
  };

  return (
    <div className="editorial-card" aria-label="Early Warning Signals">
      <div className="editorial-card-header">
        <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3>Early-Warning Intelligence Panel</h3>
            <span className="data-status-tag" style={{ fontSize: '9.5px', padding: '2px 6px' }}>CALIBRATED BASELINE</span>
          </div>
          <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>
            Ranked risk signals evaluated across gap magnitude, persistence, and evidence completeness.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#78716c' }}>
          <AlertTriangle size={13} style={{ color: '#c2410c' }} />
          <span>{filteredAlerts.length} Active Signals</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filteredAlerts.map((alert) => {
          const cardType = alert.alertType === 'SHORTAGE_RISK' ? 'shortage' : alert.alertType === 'OVERSUPPLY_RISK' ? 'oversupply' : 'warning';

          return (
            <article key={alert.id} className={`risk-item-card ${cardType}`}>
              <div className="risk-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {getAlertIcon(alert.alertType)}
                  <span className="risk-title">{getAlertTitle(alert.alertType)}</span>
                  <span style={{ fontSize: '10.5px', fontFamily: 'monospace', background: '#f5f5f4', padding: '1px 5px', borderRadius: '2px', color: '#57534e' }}>
                    {alert.district}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '10.5px', fontFamily: 'monospace', color: '#78716c' }}>
                    NCO {alert.ncoCode}
                  </span>
                  <span
                    className={`ledger-badge ${
                      alert.projectedGap > 0 ? 'shortage' : alert.projectedGap < 0 ? 'surplus' : 'balanced'
                    }`}
                    style={{ fontSize: '10px' }}
                  >
                    {formatSignedNumber(alert.projectedGap)} ({formatGapRate(alert.gapRate)})
                  </span>
                </div>
              </div>

              <div style={{ fontWeight: 600, fontSize: '13px', color: '#1c1917' }}>
                {alert.occupation}
              </div>

              <div className="risk-evidence">
                <strong>Evidence:</strong> {alert.evidenceSummary}
              </div>

              <div className="risk-caveat">
                <strong>Uncertainty / Caveat:</strong> {alert.uncertaintyNote}
              </div>

              <div className="risk-action">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                  <FileCheck size={13} style={{ marginTop: '2px', flexShrink: 0 }} />
                  <div>
                    <strong>Action for Planners:</strong> {alert.recommendedAction}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
};
