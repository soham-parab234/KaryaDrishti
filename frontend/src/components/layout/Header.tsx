import React from 'react';
import { Menu, Calendar, MapPin } from 'lucide-react';
import type { NavigationView, PilotDistrict } from '../../types/lmis';

interface HeaderProps {
  currentView: NavigationView;
  selectedDistrict: PilotDistrict;
  onChangeDistrict: (district: PilotDistrict) => void;
  onOpenMobileNav: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  selectedDistrict,
  onChangeDistrict,
  onOpenMobileNav,
}) => {
  const getSectionTitle = () => {
    switch (currentView) {
      case 'overview':
        return {
          title: 'Labour Market Intelligence Overview',
          subtitle: 'Maharashtra Pilot Analysis — Pune & Nashik Industrial Corridors',
        };
      case 'occupations':
        return {
          title: 'Occupation Explorer & Taxonomy Mapping',
          subtitle: 'NCO-2015 Classification, Title Normalization & Review Queue',
        };
      case 'forecasts':
        return {
          title: 'Demand-Supply Forecasts & Early Warnings',
          subtitle: 'Baseline Time-Series Evaluation, MAE Tracking & Actionable Risk Signals',
        };
      case 'scenarios':
        return {
          title: 'Training Seat Scenario Planner',
          subtitle: 'Deterministic Seat Allocation Simulation & Transition Yield Modelling',
        };
      case 'reports':
        return {
          title: 'Data Ingestion & Evidence Reports',
          subtitle: 'Source Lineage, Audit Trails, and Exportable Planning Briefs',
        };
      case 'assistant':
        return {
          title: 'AI Intelligence Assistant & Decision Support',
          subtitle: 'Grounded Analytical Inquiries, Demand-Supply Reasoning & Decision Support',
        };
      default:
        return {
          title: 'Labour Market Intelligence Overview',
          subtitle: 'Maharashtra Pilot Analysis — Pune & Nashik Industrial Corridors',
        };
    }
  };

  const { title, subtitle } = getSectionTitle();

  return (
    <header className="top-header" role="banner">
      <div className="header-left">
        <button
          type="button"
          className="mobile-nav-toggle"
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
        >
          <Menu size={22} />
        </button>
        <div className="header-title-group">
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>

      <div className="header-right">
        {/* District Selector Filter */}
        <div className="filter-control">
          <MapPin size={14} className="text-slate-400" aria-hidden="true" />
          <label htmlFor="district-select" className="sr-only" style={{ display: 'none' }}>District Filter</label>
          <select
            id="district-select"
            value={selectedDistrict}
            onChange={(e) => onChangeDistrict(e.target.value as PilotDistrict)}
            aria-label="Filter by District"
          >
            <option value="All Districts">All Districts (Pune & Nashik)</option>
            <option value="Pune">Pune District</option>
            <option value="Nashik">Nashik District</option>
          </select>
        </div>

        {/* Period Selector */}
        <div className="filter-control">
          <Calendar size={14} className="text-slate-400" aria-hidden="true" />
          <span style={{ fontSize: '12.5px', fontWeight: 600 }}>Period:</span>
          <select defaultValue="current" aria-label="Select reporting cycle">
            <option value="current">Oct 2026 (Latest Snapshot)</option>
            <option value="q3">Q3 2026 Comprehensive</option>
            <option value="h1">H1 2026 Historical</option>
          </select>
        </div>

        {/* Data Status Indicator */}
        <div
          className="status-indicator-pill"
          title="Data Integrity: Calibrated baseline dataset with reconciled imported observations. External administrative feeds in integration readiness."
        >
          <span className="indicator-dot" aria-hidden="true"></span>
          <span>CALIBRATED BASELINE</span>
        </div>
      </div>
    </header>
  );
};
