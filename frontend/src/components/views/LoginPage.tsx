import React, { useState } from 'react';
import { KaryaDrishtiLogo } from '../layout/KaryaDrishtiLogo';
import { GovBuildingIllustration } from '../layout/GovBuildingIllustration';
import { Mail, Lock, Eye, EyeOff, Landmark, User, ArrowRight } from 'lucide-react';

interface LoginPageProps {
  onLogin: (session: { role: string; email: string; mode: 'staff' | 'public' }) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [activeTab, setActiveTab] = useState<'staff' | 'public'>('staff');
  const [email, setEmail] = useState<string>('planner@karyadrishti.in');
  const [password, setPassword] = useState<string>('••••••••');
  const [showPassword, setShowPassword] = useState<boolean>(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLogin({
      role: activeTab === 'staff' ? 'Policy Planner' : 'Public Analyst',
      email: email || 'planner@karyadrishti.in',
      mode: activeTab,
    });
  };

  const handleDemoSelect = (roleName: string) => {
    onLogin({
      role: roleName,
      email: 'planner@karyadrishti.in',
      mode: 'staff',
    });
  };

  return (
    <div className="login-page-wrapper">
      {/* Decorative top-left warm terracotta/peach corner backdrop */}
      <div className="login-corner-backdrop" aria-hidden="true" />

      <div className="login-container">
        {/* Top Branding Section with Official KaryaDrishti Logo */}
        <header className="login-header">
          <KaryaDrishtiLogo variant="login" />
        </header>

        {/* Two-Column Editorial Grid */}
        <div className="login-grid">
          {/* Left Column: Vision Headline, Policy Brief, and Classical Government Building */}
          <div className="login-left-col">
            <h1 className="login-headline">
              See the workforce.
              <br />
              Plan the skills.
              <br />
              Act before the gap.
            </h1>

            <p className="login-subtext">
              Forecast district-level job demand against qualified training supply,
              spot shortages early and test training-seat scenarios.
            </p>

            <div className="login-illustration-wrapper">
              <GovBuildingIllustration variant="login" />
            </div>
          </div>

          {/* Right Column: Editorial Rounded Login Card */}
          <div className="login-right-col">
            <div className="login-card">
              <div className="login-card-kicker">YOUR WORKSPACE. YOUR ROLE.</div>
              <h2 className="login-card-title">Welcome to KaryaDrishti</h2>
              <p className="login-card-subtitle">
                Sign in to open forecasts, scenarios and skill mapping for your role.
              </p>

              {/* Segmented Tab Controls: Staff Login vs Public View */}
              <div className="login-tab-track" role="tablist" aria-label="Login Mode">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'staff'}
                  className={`login-tab-btn ${activeTab === 'staff' ? 'active' : ''}`}
                  onClick={() => setActiveTab('staff')}
                >
                  <Landmark size={15} />
                  <span>Staff login</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'public'}
                  className={`login-tab-btn ${activeTab === 'public' ? 'active' : ''}`}
                  onClick={() => setActiveTab('public')}
                >
                  <User size={15} />
                  <span>Public view</span>
                </button>
              </div>

              {/* Login Form */}
              <form onSubmit={handleSubmit} className="login-form">
                <div className="login-field-group">
                  <label htmlFor="login-email" className="login-label">
                    Email
                  </label>
                  <div className="login-input-container">
                    <Mail size={16} className="login-input-icon" aria-hidden="true" />
                    <input
                      id="login-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="planner@karyadrishti.in"
                      className="login-input"
                      required
                    />
                  </div>
                </div>

                <div className="login-field-group">
                  <label htmlFor="login-password" className="login-label">
                    Password
                  </label>
                  <div className="login-input-container">
                    <Lock size={16} className="login-input-icon" aria-hidden="true" />
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter password"
                      className="login-input"
                      required
                    />
                    <button
                      type="button"
                      className="login-eye-btn"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <button type="submit" className="login-submit-btn">
                  <span>Sign in</span>
                  <ArrowRight size={17} />
                </button>
              </form>

              {/* Demo Role Divider */}
              <div className="login-divider">
                <span className="login-divider-line" />
                <span className="login-divider-text">Or continue as a demo role</span>
                <span className="login-divider-line" />
              </div>

              {/* Demo Role Card: Policy Planner */}
              <div
                className="demo-role-card"
                onClick={() => handleDemoSelect('Policy Planner')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleDemoSelect('Policy Planner');
                  }
                }}
              >
                <div className="demo-role-avatar">PP</div>
                <div className="demo-role-info">
                  <div className="demo-role-name">Policy Planner</div>
                  <div className="demo-role-desc">
                    Forecasts, seat scenarios, policy brief
                  </div>
                </div>
                <div className="demo-role-arrow">
                  <ArrowRight size={16} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
