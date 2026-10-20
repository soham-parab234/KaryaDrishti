import React from 'react';
import {
  LayoutDashboard,
  Compass,
  TrendingUp,
  Sliders,
  FileSpreadsheet,
  X,
  Sparkles,
} from 'lucide-react';
import type { NavigationView } from '../../types/lmis';

interface SidebarProps {
  currentView: NavigationView;
  onSelectView: (view: NavigationView) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onSelectView,
  mobileOpen,
  onCloseMobile,
}) => {
  const navItems: { id: NavigationView; label: string; icon: React.ReactNode; badge?: string }[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <LayoutDashboard className="icon" />,
    },
    {
      id: 'occupations',
      label: 'Occupation Explorer',
      icon: <Compass className="icon" />,
      badge: 'NCO-2015',
    },
    {
      id: 'forecasts',
      label: 'Forecast & Alerts',
      icon: <TrendingUp className="icon" />,
      badge: 'Signals',
    },
    {
      id: 'scenarios',
      label: 'Scenario Planner',
      icon: <Sliders className="icon" />,
    },
    {
      id: 'reports',
      label: 'Data & Reports',
      icon: <FileSpreadsheet className="icon" />,
    },
    {
      id: 'assistant',
      label: 'AI Assistant',
      icon: <Sparkles className="icon" />,
      badge: 'Grounded',
    },
  ];

  return (
    <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`} aria-label="Main Navigation">
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <img
            src="/assets/karya-drishti-logo.png"
            alt="KaryaDrishti Logo"
            className="sidebar-logo-img"
            style={{ height: '38px', width: 'auto', objectFit: 'contain' }}
          />
          <div className="sidebar-title-group">
            <h1 style={{ fontFamily: 'Lora, serif', fontSize: '18px' }}>KaryaDrishti</h1>
            <span className="sub-label">Labour market intelligence</span>
          </div>
          {mobileOpen && (
            <button
              type="button"
              className="btn btn-outline btn-sm"
              style={{ marginLeft: 'auto', padding: '4px' }}
              onClick={onCloseMobile}
              aria-label="Close sidebar"
            >
              <X size={16} />
            </button>
          )}
        </div>
        <div className="pilot-scope-tag">
          <span className="dot" aria-hidden="true"></span>
          <span>Maharashtra Pilot System</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Core Modules</div>
        {navItems.map((item) => {
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => {
                onSelectView(item.id);
                onCloseMobile();
              }}
              aria-current={isActive ? 'page' : undefined}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge && <span className="nav-badge">{item.badge}</span>}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-status-box">
          <div className="status-row">
            <span className="status-label">Pilot Scope</span>
            <span className="status-val">Pune & Nashik</span>
          </div>
          <div className="status-row">
            <span className="status-label">Data Status</span>
            <span className="status-val" style={{ color: '#d97706' }}>SYNTHETIC BASELINE</span>
          </div>
          <div className="status-row" style={{ marginBottom: 0 }}>
            <span className="status-label">Posture</span>
            <span className="status-val" style={{ color: '#0f766e' }}>Decision Support</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
