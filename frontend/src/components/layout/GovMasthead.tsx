import React from 'react';
import type { NavigationView, PilotDistrict } from '../../types/lmis';
import { useBackendStatus } from '../../hooks/useBackendStatus';
import { API_BASE_URL } from '../../services/apiClient';

interface GovMastheadProps {
  currentView: NavigationView;
  onSelectView: (view: NavigationView) => void;
  selectedDistrict: PilotDistrict;
  onChangeDistrict: (district: PilotDistrict) => void;
  selectedSector: string;
  onChangeSector: (sector: string) => void;
}

export const GovMasthead: React.FC<GovMastheadProps> = ({
  currentView,
  onSelectView,
  selectedDistrict,
  onChangeDistrict,
  selectedSector,
  onChangeSector,
}) => {
  const { isConnected, latencyMs, error, checkConnection } = useBackendStatus();
  const navTabs: { id: NavigationView; label: string }[] = [

    { id: 'overview', label: 'Overview' },
    { id: 'occupations', label: 'Occupation Explorer' },
    { id: 'forecasts', label: 'Forecast & Alerts' },
    { id: 'scenarios', label: 'Scenario Planner' },
    { id: 'reports', label: 'Data & Reports' },
    { id: 'assistant', label: 'AI Assistant' },
  ];

  const getViewBreadcrumb = () => {
    switch (currentView) {
      case 'overview':
        return 'Overview Briefing';
      case 'occupations':
        return 'Occupation Explorer & Taxonomy';
      case 'forecasts':
        return 'Demand-Supply Forecasts & Early Warnings';
      case 'scenarios':
        return 'Training Seat Scenario Planner';
      case 'reports':
        return 'Data Ingestion & Reports';
      case 'assistant':
        return 'AI Intelligence Assistant & Decision Support';
      default:
        return 'Overview Briefing';
    }
  };

  return (
    <header className="top-masthead" role="banner">
      {/* Top Utility Accessibility Bar (GovSync reference) */}
      <div className="masthead-utility-bar">
        <span>National Labour Market Intelligence System</span>
        <span>•</span>
        <span>Skill Demand–Supply Intelligence &amp; Forecasting</span>
        <span>•</span>
        <div className="text-sizer" title="Accessibility Font Sizing">
          <span>A-</span>
          <span style={{ fontWeight: 700 }}>A</span>
          <span>A+</span>
        </div>
      </div>

      {/* Main Masthead Banner */}
      <div className="masthead-main">
        <div className="brand-section">
          <img
            src="/lmis-logo.png"
            alt="LMIS — Labour Market Intelligence System Logo"
            className="brand-logo-img"
          />
          <div className="brand-text-group">
            <h1>LMIS — Labour Market Intelligence System</h1>
            <div className="brand-sub">
              Skill Demand–Supply Intelligence, Predictive Forecasting &amp; Policy Decision Support
            </div>
          </div>
        </div>

        {/* Primary Horizontal Navigation Tabs with Terracotta Underline */}
        <nav className="masthead-nav" aria-label="Primary Navigation">
          {navTabs.map((tab) => {
            const isActive = currentView === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                className={`nav-link-btn ${isActive ? 'active' : ''}`}
                onClick={() => onSelectView(tab.id)}
                aria-current={isActive ? 'page' : undefined}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Right Status Indicators: Backend Connection + Data Provenance */}
        <div className="masthead-actions" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isConnected ? (
            <div
              className="data-status-tag"
              style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#065f46', cursor: 'pointer' }}
              title={`Operational backend connected at ${API_BASE_URL || 'http://127.0.0.1:8000'} (${latencyMs}ms). Database: SQLite`}
              onClick={checkConnection}
            >
              <span className="pulse-dot" style={{ background: '#10b981' }} aria-hidden="true"></span>
              <span>API OPERATIONAL</span>
            </div>
          ) : (
            <div
              className="data-status-tag"
              style={{ background: '#fffbeb', borderColor: '#fde68a', color: '#92400e', cursor: 'pointer' }}
              title={`Backend offline (${error || 'connection refused'}). Using local cached baseline dataset. Click to retry.`}
              onClick={checkConnection}
            >
              <span className="pulse-dot" style={{ background: '#f59e0b' }} aria-hidden="true"></span>
              <span>LOCAL BASELINE MODE</span>
            </div>
          )}

          <div
            className="data-status-tag"
            title="Data Provenance: Baseline calibration for Maharashtra pilot region (Pune & Nashik). National administrative portal connectors in integration readiness."
          >
            <span>CALIBRATED BASELINE</span>
          </div>
        </div>
      </div>


      {/* Contextual Workspace Ribbon with Integrated Analytical Filters */}
      <div className="workspace-ribbon">
        <div className="ribbon-breadcrumb">
          <span>Home</span>
          <span className="sep">/</span>
          <span>Maharashtra Pilot Corridor (Pune &amp; Nashik)</span>
          <span className="sep">/</span>
          <strong>{getViewBreadcrumb()}</strong>
        </div>

        <div className="ribbon-controls">
          {/* District Filter */}
          <div className="ribbon-filter">
            <label htmlFor="ribbon-district">District:</label>
            <select
              id="ribbon-district"
              value={selectedDistrict}
              onChange={(e) => onChangeDistrict(e.target.value as PilotDistrict)}
              aria-label="Filter by Pilot District"
            >
              <option value="All Districts">All Pilot Districts (Pune &amp; Nashik)</option>
              <option value="Pune">Pune District</option>
              <option value="Nashik">Nashik District</option>
            </select>
          </div>

          {/* Sector Filter */}
          <div className="ribbon-filter">
            <label htmlFor="ribbon-sector">Sector:</label>
            <select
              id="ribbon-sector"
              value={selectedSector}
              onChange={(e) => onChangeSector(e.target.value)}
              aria-label="Filter by Sector"
            >
              <option value="ALL">All Monitored Sectors</option>
              <option value="Clean Tech & Renewable Energy">Clean Tech &amp; Solar</option>
              <option value="Advanced Manufacturing">Adv. Manufacturing</option>
              <option value="IT & IT-Enabled Services">IT &amp; IT-Enabled Services</option>
            </select>
          </div>

          {/* Snapshot Period */}
          <div className="ribbon-filter">
            <label htmlFor="ribbon-period">Cycle:</label>
            <select id="ribbon-period" defaultValue="oct26" aria-label="Reporting Cycle">
              <option value="oct26">Oct 2026 (Latest Snapshot)</option>
              <option value="q3">Q3 2026 Cumulative</option>
              <option value="h1">H1 2026 Reference</option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
