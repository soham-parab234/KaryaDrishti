import { useState, useEffect } from 'react';
import { LoginPage } from './components/views/LoginPage';
import { DashboardHeader } from './components/layout/DashboardHeader';
import { DashboardOverview } from './components/views/DashboardOverview';
import { OccupationExplorerView } from './components/views/OccupationExplorerView';
import { ForecastAlertsView } from './components/views/ForecastAlertsView';
import { ScenarioPlannerView } from './components/views/ScenarioPlannerView';
import { DataReportsView } from './components/views/DataReportsView';
import { AiAssistantView } from './components/views/AiAssistantView';
import { AiAssistantDrawer } from './components/assistant/AiAssistantDrawer';
import {
  SYNTHETIC_OCCUPATIONS,
  SYNTHETIC_ALERTS,
} from './data/syntheticData';
import { apiClient } from './services/apiClient';
import type { BackendGapIndicator, BackendAlertItem } from './services/apiClient';
import type {
  NavigationView,
  PilotDistrict,
  OccupationSummary,
  EarlyWarningSignal,
  DataStatusLabel,
  RiskLevel,
  AlertType,
} from './types/lmis';
import './App.css';

interface UserSession {
  isAuthenticated: boolean;
  role: string;
  email: string;
  mode: 'staff' | 'public';
}

export function App() {
  // Session authentication state (defaults to login page unless previously authenticated or specified in hash)
  const [session, setSession] = useState<UserSession>(() => {
    if (typeof window !== 'undefined') {
      if (window.location.hash === '#login') {
        return {
          isAuthenticated: false,
          role: 'Policy Planner',
          email: 'planner@karyadrishti.in',
          mode: 'staff',
        };
      }
      if (window.location.hash === '#dashboard') {
        return {
          isAuthenticated: true,
          role: 'Policy Planner',
          email: 'planner@karyadrishti.in',
          mode: 'staff',
        };
      }
      const saved = localStorage.getItem('karyadrishti_session') || localStorage.getItem('lmis_session');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          // ignore corrupted storage
        }
      }
    }
    return {
      isAuthenticated: false,
      role: 'Policy Planner',
      email: 'planner@karyadrishti.in',
      mode: 'staff',
    };
  });

  const [currentView, setCurrentView] = useState<NavigationView>(() => {
    if (typeof window !== 'undefined') {
      const hash = window.location.hash;
      if (hash === '#forecasts') return 'forecasts';
      if (hash === '#scenarios') return 'scenarios';
      if (hash === '#occupations' || hash === '#skills') return 'occupations';
      if (hash === '#reports') return 'reports';
      if (hash === '#assistant') return 'assistant';
    }
    return 'overview';
  });
  const [selectedDistrict, setSelectedDistrict] = useState<PilotDistrict>('All Districts');
  const [selectedSector, setSelectedSector] = useState<string>('ALL');
  const [selectedCycle, setSelectedCycle] = useState<string>('oct26');

  // Analytical datasets connected to backend with synthetic fallbacks
  const [occupations, setOccupations] = useState<OccupationSummary[]>(SYNTHETIC_OCCUPATIONS);
  const [alerts, setAlerts] = useState<EarlyWarningSignal[]>(SYNTHETIC_ALERTS);

  // Fetch backend analytics if operational
  useEffect(() => {
    let isMounted = true;
    const loadBackendData = async () => {
      try {
        const gaps: BackendGapIndicator[] = await apiClient.getGaps(selectedDistrict);
        if (!isMounted) return;
        if (gaps && gaps.length > 0) {
          const updated = SYNTHETIC_OCCUPATIONS.map((baseOcc) => {
            const match = gaps.find(
              (g) =>
                g.nco_code === baseOcc.ncoCode &&
                g.district_code === (baseOcc.district === 'Pune' ? 'MH_PUN' : 'MH_NSK')
            );
            if (match) {
              const isShortage = match.absolute_gap > 0;
              const dynamicRisk: RiskLevel = isShortage
                ? match.gap_rate_pct !== null && match.gap_rate_pct > 25
                  ? 'CRITICAL_SHORTAGE'
                  : 'MODERATE_SHORTAGE'
                : match.absolute_gap < -50
                ? 'POTENTIAL_OVERSUPPLY'
                : 'BALANCED';
              return {
                ...baseOcc,
                documentedDemand: match.demand_value,
                qualifiedSupply: match.qualified_supply_value,
                absoluteGap: match.absolute_gap,
                gapRate: match.gap_rate_pct,
                riskLevel: dynamicRisk,
                caveat: match.limitations?.[0] || baseOcc.caveat,
                sourceStatus: (match.data_status === 'IMPORTED'
                  ? 'IMPORTED'
                  : 'SYNTHETIC BASELINE') as DataStatusLabel,
              };
            }
            return baseOcc;
          });
          setOccupations(updated);
        }

        const backendAlerts: BackendAlertItem[] = await apiClient.getAlerts(selectedDistrict);
        if (!isMounted) return;
        if (backendAlerts && backendAlerts.length > 0) {
          const mappedAlerts: EarlyWarningSignal[] = backendAlerts.map((a) => ({
            id: a.alert_id,
            alertType: (a.alert_type === 'DATA_QUALITY_WARNING'
              ? 'DATA_WARNING'
              : a.alert_type) as AlertType,
            severity:
              a.severity === 'CRITICAL' ? 'HIGH' : a.severity === 'WARNING' ? 'MEDIUM' : 'LOW',
            triageStatus: 'NEW',
            occupation: a.canonical_title || `NCO ${a.nco_code}`,
            ncoCode: a.nco_code,
            district:
              a.district_code === 'MH_PUN'
                ? 'Pune'
                : a.district_code === 'MH_NSK'
                ? 'Nashik'
                : a.district_code,
            projectedGap: a.absolute_gap || 0,
            gapRate: a.gap_rate_pct,
            evidenceSummary: a.evidence_summary,
            uncertaintyNote: a.trigger_rule,
            recommendedAction: a.review_action_recommended,
            sourceStatus: 'SYNTHETIC BASELINE',
            detectedAt: a.created_at ? a.created_at.split('T')[0] : '2026-10-18',
          }));
          setAlerts(mappedAlerts);
        }
      } catch {
        // Fall back gracefully to calibrated synthetic baseline
      }
    };

    loadBackendData();
    return () => {
      isMounted = false;
    };
  }, [selectedDistrict]);

  // Synchronize URL hash with view and auth state
  useEffect(() => {
    const handleHashSync = () => {
      const hash = window.location.hash;
      if (hash === '#login') {
        setSession((prev) => ({ ...prev, isAuthenticated: false }));
      } else if (hash === '#dashboard' || hash === '#overview') {
        setCurrentView('overview');
      } else if (hash === '#forecasts') {
        setCurrentView('forecasts');
      } else if (hash === '#scenarios') {
        setCurrentView('scenarios');
      } else if (hash === '#occupations' || hash === '#skills') {
        setCurrentView('occupations');
      } else if (hash === '#reports') {
        setCurrentView('reports');
      } else if (hash === '#assistant') {
        setCurrentView('assistant');
      }
    };

    window.addEventListener('hashchange', handleHashSync);
    return () => window.removeEventListener('hashchange', handleHashSync);
  }, []);

  const handleSelectView = (view: NavigationView) => {
    setCurrentView(view);
    const hashMap: Record<NavigationView, string> = {
      overview: '#dashboard',
      forecasts: '#forecasts',
      scenarios: '#scenarios',
      occupations: '#occupations',
      reports: '#reports',
      assistant: '#assistant',
    };
    if (typeof window !== 'undefined') {
      window.location.hash = hashMap[view] || '#dashboard';
    }
  };

  const handleLogin = (newSession: { role: string; email: string; mode: 'staff' | 'public' }) => {
    const updated: UserSession = {
      isAuthenticated: true,
      role: newSession.role,
      email: newSession.email,
      mode: newSession.mode,
    };
    setSession(updated);
    try {
      localStorage.setItem('karyadrishti_session', JSON.stringify(updated));
      localStorage.setItem('lmis_session', JSON.stringify(updated));
      window.location.hash = '#dashboard';
    } catch {
      // ignore
    }
  };

  const handleSignOut = () => {
    const updated: UserSession = {
      isAuthenticated: false,
      role: 'Policy Planner',
      email: 'planner@karyadrishti.in',
      mode: 'staff',
    };
    setSession(updated);
    try {
      localStorage.removeItem('karyadrishti_session');
      localStorage.removeItem('lmis_session');
      window.location.hash = '#login';
    } catch {
      // ignore
    }
  };

  // If not authenticated, render the dedicated Login Page matching Image 1
  if (!session.isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />;
  }

  // Active view router within the dashboard
  const renderActiveView = () => {
    switch (currentView) {
      case 'overview':
        return (
          <DashboardOverview
            occupations={occupations}
            alerts={alerts}
            selectedDistrict={selectedDistrict}
            selectedSector={selectedSector}
            selectedCycle={selectedCycle}
            onChangeDistrict={setSelectedDistrict}
            onChangeSector={setSelectedSector}
          />
        );
      case 'occupations':
        return (
          <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 32px' }}>
            <OccupationExplorerView
              selectedDistrict={selectedDistrict}
              selectedSector={selectedSector}
            />
          </div>
        );
      case 'forecasts':
        return (
          <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 32px' }}>
            <ForecastAlertsView
              selectedDistrict={selectedDistrict}
              selectedSector={selectedSector}
            />
          </div>
        );
      case 'scenarios':
        return (
          <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 32px' }}>
            <ScenarioPlannerView
              selectedDistrict={selectedDistrict}
              selectedSector={selectedSector}
            />
          </div>
        );
      case 'reports':
        return (
          <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 32px' }}>
            <DataReportsView />
          </div>
        );
      case 'assistant':
        return (
          <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 32px' }}>
            <AiAssistantView
              selectedDistrict={selectedDistrict}
              onChangeDistrict={setSelectedDistrict}
            />
          </div>
        );
      default:
        return (
          <DashboardOverview
            occupations={occupations}
            alerts={alerts}
            selectedDistrict={selectedDistrict}
            selectedSector={selectedSector}
            selectedCycle={selectedCycle}
            onChangeDistrict={setSelectedDistrict}
            onChangeSector={setSelectedSector}
          />
        );
    }
  };

  return (
    <div
      className="app-container"
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        background: 'var(--bg-parchment)',
      }}
    >
      {/* Top KaryaDrishti Dashboard Header, Navigation & Global Filter Bar */}
      <DashboardHeader
        currentView={currentView}
        onSelectView={handleSelectView}
        onSignOut={handleSignOut}
        roleName={session.role}
        roleSubtitle={session.mode === 'staff' ? 'Policy Planner' : 'Public Viewer'}
        selectedDistrict={selectedDistrict}
        onChangeDistrict={setSelectedDistrict}
        selectedSector={selectedSector}
        onChangeSector={setSelectedSector}
        selectedCycle={selectedCycle}
        onChangeCycle={setSelectedCycle}
      />

      {/* Main Analytical Content Viewport */}
      <main style={{ flex: 1 }}>{renderActiveView()}</main>

      {/* Floating AI Intelligence Assistant Drawer */}
      <AiAssistantDrawer selectedDistrict={selectedDistrict} />
    </div>
  );
}

export default App;
