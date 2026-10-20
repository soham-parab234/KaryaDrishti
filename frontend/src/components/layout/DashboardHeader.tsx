import React from 'react';
import { KaryaDrishtiLogo } from './KaryaDrishtiLogo';
import type { NavigationView, PilotDistrict } from '../../types/lmis';
import { LogOut, ShieldCheck, RefreshCw } from 'lucide-react';
import { useBackendStatus } from '../../hooks/useBackendStatus';

interface DashboardHeaderProps {
  currentView: NavigationView;
  onSelectView: (view: NavigationView) => void;
  onSignOut: () => void;
  roleName: string;
  roleSubtitle?: string;
  selectedDistrict: PilotDistrict;
  onChangeDistrict: (district: PilotDistrict) => void;
  selectedSector: string;
  onChangeSector: (sector: string) => void;
  selectedCycle?: string;
  onChangeCycle?: (cycle: string) => void;
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
}) => {
  const { isConnected, latencyMs, checkConnection } = useBackendStatus();

  const navTabs: { id: NavigationView; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'forecasts', label: 'Forecasts' },
    { id: 'scenarios', label: 'Scenarios' },
    { id: 'occupations', label: 'Skills match' },
    { id: 'reports', label: 'Data & Reports' },
    { id: 'assistant', label: 'AI Assistant' },
  ];

  return (
    <header className="karya-header-wrapper" role="banner">
      {/* 1. Top Bar: Logo on left, Sign Out and Status on right */}
      <div className="karya-header-top">
        <div className="karya-header-brand">
          <KaryaDrishtiLogo variant="header" height={46} />
        </div>

        <div className="karya-header-actions" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Subtle Backend Status indicator */}
          <button
            type="button"
            className="karya-status-pill"
            onClick={checkConnection}
            title={
              isConnected
                ? `Operational backend connected (${latencyMs}ms). Database: SQLite`
                : 'Using local calibrated baseline dataset. Click to retry.'
            }
          >
            <span
              className="karya-status-dot"
              style={{ backgroundColor: isConnected ? '#10b981' : '#f59e0b' }}
              aria-hidden="true"
            />
            <span>{isConnected ? 'API Connected' : 'Baseline Mode'}</span>
            <RefreshCw size={12} className="karya-status-refresh" />
          </button>

          {/* Sign Out Button matching Reference Image 2 & 3 */}
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

      {/* 2. Primary Horizontal Navigation Bar matching Reference Image 2 */}
      <div className="karya-header-nav">
        {navTabs.map((tab) => {
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
      </div>

      {/* 3. Slim Workspace Strip matching Reference Image 2 & 3 */}
      <div className="karya-subbar">
        <div className="karya-subbar-left">
          <div className="karya-subbar-role">
            <span className="karya-role-name">{roleName}</span>
            <span className="karya-role-desc">{roleSubtitle}</span>
          </div>

          <div className="karya-subbar-divider" />

          {/* District Selector Filter */}
          <div className="karya-header-filter">
            <label htmlFor="workspace-district-select">District:</label>
            <div className="karya-select-wrapper">
              <select
                id="workspace-district-select"
                value={selectedDistrict}
                onChange={(e) => onChangeDistrict(e.target.value as PilotDistrict)}
                className="karya-subbar-select"
                aria-label="Filter by Pilot District"
              >
                <option value="All Districts">All Pilot Districts (Pune &amp; Nashik)</option>
                <option value="Pune">Pune District</option>
                <option value="Nashik">Nashik District</option>
              </select>
            </div>
          </div>

          {/* Sector Selector Filter */}
          <div className="karya-header-filter">
            <label htmlFor="workspace-sector-select">Sector:</label>
            <div className="karya-select-wrapper">
              <select
                id="workspace-sector-select"
                value={selectedSector}
                onChange={(e) => onChangeSector(e.target.value)}
                className="karya-subbar-select"
                aria-label="Filter by Sector"
              >
                <option value="ALL">All Sectors</option>
                <option value="Clean Tech & Renewable Energy">Clean Tech &amp; Solar</option>
                <option value="Advanced Manufacturing">Adv. Manufacturing</option>
                <option value="IT & IT-Enabled Services">IT &amp; IT-Enabled Services</option>
              </select>
            </div>
          </div>
        </div>

        <div className="karya-subbar-right">
          {/* Data Provenance Indicator matching screenshot */}
          <div className="karya-subbar-notice">
            <ShieldCheck size={14} className="karya-notice-icon" />
            <span>Synthetic demonstration data · Maharashtra pilot</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default DashboardHeader;
