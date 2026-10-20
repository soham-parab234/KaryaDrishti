import React from 'react';
import { KaryaDrishtiLogo } from './KaryaDrishtiLogo';
import { LogOut, ShieldCheck } from 'lucide-react';
import type { NavigationView, PilotDistrict } from '../../types/lmis';
import { useBackendStatus } from '../../hooks/useBackendStatus';

interface DashboardHeaderProps {
  currentView: NavigationView;
  onSelectView: (view: NavigationView) => void;
  onSignOut: () => void;
  roleName?: string;
  roleSubtitle?: string;
  selectedDistrict: PilotDistrict;
  onChangeDistrict: (district: PilotDistrict) => void;
  selectedSector: string;
  onChangeSector: (sector: string) => void;
  selectedCycle: string;
  onChangeCycle: (cycle: string) => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  currentView,
  onSelectView,
  onSignOut,
  roleName = 'Policy Planner',
  roleSubtitle = 'Policy Planner',
  selectedDistrict,
  onChangeDistrict,
  selectedSector,
  onChangeSector,
  selectedCycle,
  onChangeCycle,
}) => {
  const { isConnected, latencyMs, checkConnection } = useBackendStatus();

  const tabs: { id: NavigationView; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'forecasts', label: 'Forecasts' },
    { id: 'scenarios', label: 'Scenarios' },
    { id: 'occupations', label: 'Skills match' },
    { id: 'reports', label: 'Data & Reports' },
    { id: 'assistant', label: 'AI Assistant' },
  ];

  return (
    <header className="karya-header-wrapper" role="banner">
      {/* Top Navbar Row: Logo on Left, Operational Status & Sign Out on Right */}
      <div className="karya-header-top">
        <div className="karya-header-brand">
          <KaryaDrishtiLogo variant="header" />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Backend Connection Health Badge */}
          {isConnected ? (
            <div
              className="lmis-status-pill operational"
              onClick={checkConnection}
              title={`API Operational (${latencyMs}ms). Database: SQLite.`}
              role="status"
            >
              <span className="pulse-dot active" aria-hidden="true" />
              <span>API OPERATIONAL</span>
            </div>
          ) : (
            <div
              className="lmis-status-pill baseline"
              onClick={checkConnection}
              title="Running on client-side calibrated baseline dataset. Click to retry connection."
              role="status"
            >
              <span className="pulse-dot baseline" aria-hidden="true" />
              <span>LOCAL BASELINE</span>
            </div>
          )}

          <button
            type="button"
            className="karya-signout-btn"
            onClick={onSignOut}
            aria-label="Sign out of KaryaDrishti"
          >
            <LogOut size={15} />
            <span>Sign out</span>
          </button>
        </div>
      </div>

      {/* Primary Navigation Tabs with Terracotta Underline Indicator */}
      <nav className="karya-header-nav" aria-label="Main Navigation">
        {tabs.map((tab) => {
          const isActive = currentView === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              className={`karya-nav-tab ${isActive ? 'active' : ''}`}
              onClick={() => onSelectView(tab.id)}
              aria-current={isActive ? 'page' : undefined}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Secondary Context & Global Analytical Filters Bar */}
      <div className="karya-subbar">
        <div className="karya-subbar-left">
          <div className="karya-subbar-role">
            <span className="karya-role-name">{roleName}</span>
            <span className="karya-role-desc">{roleSubtitle}</span>
          </div>

          <div className="karya-subbar-divider" aria-hidden="true" />

          {/* Global Filter: District */}
          <div className="karya-header-filter">
            <label htmlFor="global-district-select">District:</label>
            <select
              id="global-district-select"
              value={selectedDistrict}
              onChange={(e) => onChangeDistrict(e.target.value as PilotDistrict)}
              aria-label="Select Pilot District"
              className="karya-subbar-select"
            >
              <option value="All Districts">All Pilot Districts (Pune &amp; Nashik)</option>
              <option value="Pune">Pune District</option>
              <option value="Nashik">Nashik District</option>
            </select>
          </div>

          {/* Global Filter: Sector */}
          <div className="karya-header-filter">
            <label htmlFor="global-sector-select">Sector:</label>
            <select
              id="global-sector-select"
              value={selectedSector}
              onChange={(e) => onChangeSector(e.target.value)}
              aria-label="Select Industry Sector"
              className="karya-subbar-select"
            >
              <option value="ALL">All Monitored Sectors</option>
              <option value="Clean Tech & Renewable Energy">Clean Tech &amp; Renewable</option>
              <option value="Advanced Manufacturing">Adv. Manufacturing</option>
              <option value="IT & IT-Enabled Services">IT &amp; IT-Enabled Services</option>
            </select>
          </div>

          {/* Global Filter: Reporting Cycle */}
          <div className="karya-header-filter">
            <label htmlFor="global-cycle-select">Cycle:</label>
            <select
              id="global-cycle-select"
              value={selectedCycle}
              onChange={(e) => onChangeCycle(e.target.value)}
              aria-label="Select Reporting Cycle"
              className="karya-subbar-select"
            >
              <option value="oct26">Oct 2026 (Latest Snapshot)</option>
              <option value="q3">Q3 2026 Cumulative</option>
              <option value="h1">H1 2026 Reference</option>
            </select>
          </div>
        </div>

        <div className="karya-subbar-notice">
          <ShieldCheck size={14} className="karya-notice-icon" aria-hidden="true" />
          <span>Synthetic demonstration data · Maharashtra pilot</span>
        </div>
      </div>
    </header>
  );
};
