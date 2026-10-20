import { useState } from 'react';
import { GovMasthead } from './components/layout/GovMasthead';
import { OverviewView } from './components/views/OverviewView';
import { OccupationExplorerView } from './components/views/OccupationExplorerView';
import { ForecastAlertsView } from './components/views/ForecastAlertsView';
import { ScenarioPlannerView } from './components/views/ScenarioPlannerView';
import { DataReportsView } from './components/views/DataReportsView';
import { AiAssistantView } from './components/views/AiAssistantView';
import { AiAssistantDrawer } from './components/assistant/AiAssistantDrawer';
import type { NavigationView, PilotDistrict } from './types/lmis';
import { ShieldCheck, Info } from 'lucide-react';
import './App.css';

export function App() {
  const [currentView, setCurrentView] = useState<NavigationView>('overview');
  const [selectedDistrict, setSelectedDistrict] = useState<PilotDistrict>('All Districts');
  const [selectedSector, setSelectedSector] = useState<string>('ALL');

  const renderActiveView = () => {
    switch (currentView) {
      case 'overview':
        return (
          <OverviewView
            selectedDistrict={selectedDistrict}
            selectedSector={selectedSector}
          />
        );
      case 'occupations':
        return (
          <OccupationExplorerView
            selectedDistrict={selectedDistrict}
            selectedSector={selectedSector}
          />
        );
      case 'forecasts':
        return (
          <ForecastAlertsView
            selectedDistrict={selectedDistrict}
            selectedSector={selectedSector}
          />
        );
      case 'scenarios':
        return (
          <ScenarioPlannerView
            selectedDistrict={selectedDistrict}
            selectedSector={selectedSector}
          />
        );
      case 'reports':
        return <DataReportsView />;
      case 'assistant':
        return (
          <AiAssistantView
            selectedDistrict={selectedDistrict}
            onChangeDistrict={setSelectedDistrict}
          />
        );
      default:
        return (
          <OverviewView
            selectedDistrict={selectedDistrict}
            selectedSector={selectedSector}
          />
        );
    }
  };

  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-parchment)' }}>
      {/* GovSync-Inspired Institutional Masthead & Navigation */}
      <GovMasthead
        currentView={currentView}
        onSelectView={setCurrentView}
        selectedDistrict={selectedDistrict}
        onChangeDistrict={setSelectedDistrict}
        selectedSector={selectedSector}
        onChangeSector={setSelectedSector}
      />

      {/* Main Analytical Viewport */}
      <main style={{ flex: 1 }}>{renderActiveView()}</main>

      {/* Floating AI Intelligence Assistant Drawer */}
      <AiAssistantDrawer selectedDistrict={selectedDistrict} />

      {/* Institutional Editorial Footer */}
      <footer className="editorial-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={15} style={{ color: '#0f766e' }} />
          <span>
            <strong>LMIS — Labour Market Intelligence System</strong>
          </span>
          <span style={{ color: '#d6d3d1' }}>|</span>
          <span>National Skill Demand–Supply Forecasting &amp; Policy Decision Support Platform</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Info size={13} style={{ color: '#c2410c' }} />
          <span>
            Maharashtra Pilot Region (Pune &amp; Nashik) • Calibrated Baseline Data &amp; Operational Analytics
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
