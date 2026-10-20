import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  Database,
  AlertTriangle,
  ShieldCheck,
  RotateCcw,
  Loader2,
  ChevronDown,
  ChevronUp,
  Info,
  TrendingUp,
  AlertCircle,
  GraduationCap,
  Layers,
  HelpCircle,
} from 'lucide-react';
import { apiClient } from '../../services/apiClient';
import type { AiQueryResponse, PilotDistrict } from '../../types/lmis';

interface AiAssistantViewProps {
  selectedDistrict: PilotDistrict;
  onChangeDistrict?: (district: PilotDistrict) => void;
}

interface SuggestedPrompt {
  id: string;
  category: string;
  question: string;
  description: string;
  icon: React.ReactNode;
}

const SUGGESTED_QUESTIONS: SuggestedPrompt[] = [
  {
    id: 'shortages',
    category: 'SHORTAGE DIAGNOSTICS',
    question: 'Which occupations have the largest skill shortages?',
    description: 'Ranks severe demand-supply deficits across pilot manufacturing & clean-tech corridors.',
    icon: <TrendingUp size={16} style={{ color: '#c2410c' }} />,
  },
  {
    id: 'forecast',
    category: 'TIME-SERIES FORECASTING',
    question: 'Explain the forecast for an occupation.',
    description: 'Inspects projected demand horizons, chronological backtest MAE, and analytical intervals.',
    icon: <Layers size={16} style={{ color: '#0369a1' }} />,
  },
  {
    id: 'alerts',
    category: 'EARLY WARNING SIGNALS',
    question: 'Which alerts need attention?',
    description: 'Lists active shortage risks, data-quality warnings, and recommended triage actions.',
    icon: <AlertTriangle size={16} style={{ color: '#d97706' }} />,
  },
  {
    id: 'training',
    category: 'SKILLING INTERVENTIONS',
    question: 'What training interventions could address the identified gaps?',
    description: 'Evaluates sanctioned training seats vs qualified supply and proposed ITI capacity expansions.',
    icon: <GraduationCap size={16} style={{ color: '#0f766e' }} />,
  },
  {
    id: 'limitations',
    category: 'DATA INTEGRITY & METHODOLOGY',
    question: 'What data limitations affect these findings?',
    description: 'Audits synthetic vs imported provenance, non-vacancy demand signals, and survey caveats.',
    icon: <HelpCircle size={16} style={{ color: '#78716c' }} />,
  },
];

export const AiAssistantView: React.FC<AiAssistantViewProps> = ({
  selectedDistrict,
  onChangeDistrict,
}) => {
  const [queryInput, setQueryInput] = useState('');
  const [activeQuery, setActiveQuery] = useState<string>('');
  const [lastAttemptedQuery, setLastAttemptedQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [emptyInputError, setEmptyInputError] = useState<boolean>(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [response, setResponse] = useState<AiQueryResponse | null>(null);

  const [evidenceExpanded, setEvidenceExpanded] = useState<boolean>(true);
  const [limitationsExpanded, setLimitationsExpanded] = useState<boolean>(true);

  const resultContainerRef = useRef<HTMLDivElement>(null);

  const handleExecuteQuery = useCallback(
    async (textToSubmit?: string) => {
      const q = (textToSubmit !== undefined ? textToSubmit : queryInput).trim();
      if (!q) {
        setEmptyInputError(true);
        return;
      }

      setEmptyInputError(false);
      setRequestError(null);
      setActiveQuery(q);
      setLastAttemptedQuery(q);
      setIsLoading(true);

      try {
        const districtCode =
          selectedDistrict === 'Pune'
            ? 'MH_PUN'
            : selectedDistrict === 'Nashik'
            ? 'MH_NSK'
            : undefined;

        const res = await apiClient.askAssistant({
          query: q,
          district_code: districtCode,
        });

        setResponse(res);
      } catch (err: unknown) {
        const msg =
          err instanceof Error
            ? err.message
            : 'Communication failure: Unable to connect to the KaryaDrishti AI Assistant endpoint.';
        setRequestError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [queryInput, selectedDistrict]
  );

  const handleRetry = () => {
    if (lastAttemptedQuery) {
      handleExecuteQuery(lastAttemptedQuery);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleExecuteQuery();
    }
  };

  // Scroll to results when response arrives
  useEffect(() => {
    if (response && resultContainerRef.current) {
      resultContainerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [response]);

  // Markdown-like simple renderer for structured bullet points and bold headers
  const renderFormattedAnswer = (text: string) => {
    const lines = text.split('\n');
    return (
      <div className="assistant-rendered-markdown" style={{ fontSize: '13.5px', lineHeight: '1.7', color: 'var(--stone-900)' }}>
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) {
            return <div key={idx} style={{ height: '8px' }} />;
          }

          // Section Heading (### or ####)
          if (trimmed.startsWith('####')) {
            return (
              <h4
                key={idx}
                style={{
                  fontSize: '13px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  color: 'var(--rust-700)',
                  margin: '14px 0 6px 0',
                }}
              >
                {trimmed.replace(/^####\s*/, '')}
              </h4>
            );
          }
          if (trimmed.startsWith('###')) {
            return (
              <h3
                key={idx}
                style={{
                  fontFamily: 'var(--font-serif)',
                  fontSize: '16px',
                  fontWeight: 700,
                  color: 'var(--stone-900)',
                  margin: '16px 0 8px 0',
                  borderBottom: '1px solid var(--stone-200)',
                  paddingBottom: '4px',
                }}
              >
                {trimmed.replace(/^###\s*/, '')}
              </h3>
            );
          }

          // Bullet items
          if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            const rawContent = trimmed.substring(2);
            // Replace **bold** with <strong>
            const parts = rawContent.split(/(\*\*.*?\*\*)/g);
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  marginBottom: '6px',
                  paddingLeft: '4px',
                }}
              >
                <span style={{ color: 'var(--rust-600)', fontSize: '14px', lineHeight: '1.4' }}>•</span>
                <span style={{ flex: 1 }}>
                  {parts.map((p, pIdx) => {
                    if (p.startsWith('**') && p.endsWith('**')) {
                      return <strong key={pIdx} style={{ color: 'var(--stone-900)' }}>{p.slice(2, -2)}</strong>;
                    }
                    if (p.startsWith('`') && p.endsWith('`')) {
                      return (
                        <code
                          key={pIdx}
                          style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '11.5px',
                            background: 'var(--stone-100)',
                            padding: '1px 5px',
                            borderRadius: '3px',
                            color: 'var(--stone-800)',
                          }}
                        >
                          {p.slice(1, -1)}
                        </code>
                      );
                    }
                    return p;
                  })}
                </span>
              </div>
            );
          }

          // Regular paragraph
          const parts = trimmed.split(/(\*\*.*?\*\*)/g);
          return (
            <p key={idx} style={{ marginBottom: '8px' }}>
              {parts.map((p, pIdx) => {
                if (p.startsWith('**') && p.endsWith('**')) {
                  return <strong key={pIdx} style={{ color: 'var(--stone-900)' }}>{p.slice(2, -2)}</strong>;
                }
                if (p.startsWith('`') && p.endsWith('`')) {
                  return (
                    <code
                      key={pIdx}
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11.5px',
                        background: 'var(--stone-100)',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        color: 'var(--stone-800)',
                      }}
                    >
                      {p.slice(1, -1)}
                    </code>
                  );
                }
                return p;
              })}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="view-container" style={{ padding: '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Editorial View Header */}
      <div
        style={{
          borderBottom: '2px solid var(--rust-600)',
          paddingBottom: '16px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10.5px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--rust-700)',
                background: 'var(--rust-50)',
                border: '1px solid var(--rust-100)',
                padding: '2px 8px',
                borderRadius: '4px',
              }}
            >
              AI DECISION SUPPORT &amp; GROUNDED REASONING
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10.5px',
                color: 'var(--stone-500)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <ShieldCheck size={13} style={{ color: '#0f766e' }} />
              Read-Only Governance Engine
            </span>
          </div>

          <h2
            style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '26px',
              fontWeight: 700,
              color: 'var(--stone-900)',
              letterSpacing: '-0.01em',
              margin: '4px 0 6px 0',
            }}
          >
            AI Labour Market Intelligence Assistant
          </h2>
          <p style={{ fontSize: '13.5px', color: 'var(--stone-600)', maxWidth: '850px' }}>
            Interactive natural-language briefing console grounded directly in occupational time series, qualified
            workforce estimates, sanctioned training capacity, and baseline forecasting models.
          </p>
        </div>

        {/* District Filter Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              background: '#ffffff',
              border: '1px solid var(--stone-200)',
              borderRadius: '6px',
              padding: '6px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: 'var(--shadow-subtle)',
            }}
          >
            <label htmlFor="assistant-district-select" style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--stone-600)' }}>
              Analytical Scope:
            </label>
            <select
              id="assistant-district-select"
              value={selectedDistrict}
              onChange={(e) => onChangeDistrict && onChangeDistrict(e.target.value as PilotDistrict)}
              style={{
                border: '1px solid var(--stone-300)',
                borderRadius: '4px',
                padding: '3px 8px',
                fontSize: '12px',
                fontFamily: 'inherit',
                fontWeight: 600,
                color: 'var(--stone-800)',
                background: '#ffffff',
                cursor: 'pointer',
              }}
            >
              <option value="All Districts">All Pilot Districts (Pune &amp; Nashik)</option>
              <option value="Pune">Pune District (MH_PUN)</option>
              <option value="Nashik">Nashik District (MH_NSK)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '28px', alignItems: 'start' }}>
        {/* Left Column: Suggested Strategic Questions & Architecture Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Suggested Questions Section */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid var(--stone-200)',
              borderRadius: '8px',
              padding: '18px',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Sparkles size={16} style={{ color: 'var(--rust-600)' }} />
              <h3 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--stone-800)' }}>
                Suggested Inquiries
              </h3>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--stone-600)', marginBottom: '16px', lineHeight: '1.5' }}>
              Click any question below to generate a real-time, grounded intelligence briefing with empirical &amp; synthetic data breakdown.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {SUGGESTED_QUESTIONS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setQueryInput(item.question);
                    handleExecuteQuery(item.question);
                  }}
                  disabled={isLoading}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    textAlign: 'left',
                    padding: '12px 14px',
                    borderRadius: '6px',
                    border: '1px solid var(--stone-200)',
                    background: activeQuery === item.question ? 'var(--rust-50)' : 'var(--bg-surface-subtle)',
                    borderColor: activeQuery === item.question ? 'var(--rust-600)' : 'var(--stone-200)',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s ease',
                    gap: '4px',
                  }}
                  onMouseEnter={(e) => {
                    if (!isLoading && activeQuery !== item.question) {
                      e.currentTarget.style.borderColor = 'var(--rust-600)';
                      e.currentTarget.style.background = '#ffffff';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isLoading && activeQuery !== item.question) {
                      e.currentTarget.style.borderColor = 'var(--stone-200)';
                      e.currentTarget.style.background = 'var(--bg-surface-subtle)';
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%' }}>
                    {item.icon}
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '9.5px',
                        fontWeight: 700,
                        color: 'var(--stone-500)',
                        letterSpacing: '0.04em',
                      }}
                    >
                      {item.category}
                    </span>
                  </div>
                  <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--stone-900)', marginTop: '2px' }}>
                    {item.question}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--stone-500)', lineHeight: '1.4' }}>
                    {item.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Architecture Guardrails Card */}
          <div
            style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '16px',
              fontSize: '11.5px',
              color: '#334155',
              lineHeight: '1.6',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', fontWeight: 700, color: '#0f172a' }}>
              <ShieldCheck size={15} style={{ color: '#0f766e' }} />
              <span>Grounded Architecture Guarantees</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <li>
                <strong>Strict Grounding:</strong> Intelligence answers are strictly formed from SQLite database records. The engine never invents unverified figures.
              </li>
              <li>
                <strong>Supply vs Capacity:</strong> Clearly segregates sanctioned training seats (institutional capacity) from plausibly qualified job-ready supply.
              </li>
              <li>
                <strong>Provenance Distinction:</strong> Identifies imported data signals from baseline synthetic demonstration records.
              </li>
              <li>
                <strong>Resilient Fallback:</strong> If external AI providers are offline or unconfigured, the deterministic rule-based engine synthesizes full findings instantly.
              </li>
            </ul>
          </div>
        </div>

        {/* Right Column: Query Input, Status, and Detailed Intelligence Dossier */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Query Input Bar */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid var(--stone-200)',
              borderRadius: '8px',
              padding: '16px 20px',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <label
              htmlFor="ai-query-input-field"
              style={{
                display: 'block',
                fontSize: '12.5px',
                fontWeight: 700,
                color: 'var(--stone-800)',
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '0.03em',
              }}
            >
              Ask the KaryaDrishti Forecasting Engine
            </label>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                id="ai-query-input-field"
                type="text"
                value={queryInput}
                onChange={(e) => {
                  setQueryInput(e.target.value);
                  if (emptyInputError) setEmptyInputError(false);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ask about shortages, forecasts, training seat expansion, or pilot alerts..."
                disabled={isLoading}
                style={{
                  flex: 1,
                  padding: '11px 14px',
                  borderRadius: '6px',
                  border: emptyInputError ? '1px solid #dc2626' : '1px solid var(--stone-300)',
                  fontSize: '13.5px',
                  outline: 'none',
                  fontFamily: 'inherit',
                  background: 'var(--bg-surface)',
                  transition: 'border-color 0.15s ease',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--rust-600)';
                  e.currentTarget.style.boxShadow = '0 0 0 2px rgba(194, 65, 12, 0.15)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = emptyInputError ? '#dc2626' : 'var(--stone-300)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />

              <button
                type="button"
                onClick={() => handleExecuteQuery()}
                disabled={isLoading}
                style={{
                  background: 'var(--rust-600)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '11px 20px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: 'var(--shadow-subtle)',
                  transition: 'background-color 0.15s ease',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) e.currentTarget.style.background = 'var(--rust-700)';
                }}
                onMouseLeave={(e) => {
                  if (!isLoading) e.currentTarget.style.background = 'var(--rust-600)';
                }}
                aria-label="Submit Query to AI Assistant"
              >
                {isLoading ? (
                  <>
                    <Loader2 size={16} className="spinner" style={{ animation: 'spin 1s linear infinite' }} />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Send size={15} />
                    <span>Run Query</span>
                  </>
                )}
              </button>
            </div>

            {/* Empty Input Validation Message */}
            {emptyInputError && (
              <div
                style={{
                  marginTop: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  color: '#b91c1c',
                }}
              >
                <AlertCircle size={14} />
                <span>Please enter a query or select one of the suggested inquiries from the left panel.</span>
              </div>
            )}
          </div>

          {/* Request Failure & Retry State */}
          {requestError && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '8px',
                padding: '16px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <AlertTriangle size={18} style={{ color: '#dc2626', flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#991b1b', marginBottom: '2px' }}>
                    Request Execution Failure
                  </div>
                  <div style={{ fontSize: '12px', color: '#b91c1c' }}>{requestError}</div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleRetry}
                style={{
                  background: '#ffffff',
                  border: '1px solid #fca5a5',
                  borderRadius: '5px',
                  padding: '7px 14px',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: '#991b1b',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: 'var(--shadow-subtle)',
                }}
              >
                <RotateCcw size={13} />
                <span>Retry Query</span>
              </button>
            </div>
          )}

          {/* Loading Indicator State */}
          {isLoading && (
            <div
              style={{
                background: '#ffffff',
                border: '1px solid var(--stone-200)',
                borderRadius: '8px',
                padding: '36px 24px',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <Loader2 size={28} style={{ color: 'var(--rust-600)', animation: 'spin 1s linear infinite' }} />
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--stone-800)' }}>
                Retrieving verified KaryaDrishti time series &amp; synthesizing analysis...
              </div>
              <div style={{ fontSize: '12px', color: 'var(--stone-500)', maxWidth: '480px' }}>
                Scanning DemandObservation, QualifiedSupplyEstimate, TrainingCapacityOutcome, and ForecastRun models.
              </div>
            </div>
          )}

          {/* Active Results Dossier */}
          {response && !isLoading && (
            <div
              ref={resultContainerRef}
              style={{
                background: '#ffffff',
                border: '1px solid var(--stone-200)',
                borderRadius: '8px',
                boxShadow: 'var(--shadow-card)',
                overflow: 'hidden',
              }}
            >
              {/* Dossier Header & Mode Pill */}
              <div
                style={{
                  padding: '14px 20px',
                  background: 'linear-gradient(to right, #1c1917, #292524)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px',
                  borderBottom: '2px solid var(--rust-600)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Sparkles size={16} style={{ color: '#fed7aa' }} />
                  <div>
                    <div style={{ fontSize: '13.5px', fontWeight: 700 }}>
                      Executive Intelligence Briefing
                    </div>
                    <div style={{ fontSize: '11px', color: '#a8a29e' }}>
                      Query: &ldquo;{response.query}&rdquo;
                    </div>
                  </div>
                </div>

                {/* Metadata Provider & Mode Badges */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {/* Mode Pill: Live AI vs Rule-Based Fallback */}
                  <span
                    style={{
                      background: response.mode === 'PROVIDER_LLM' ? '#dcfce7' : '#fef3c7',
                      color: response.mode === 'PROVIDER_LLM' ? '#166534' : '#92400e',
                      padding: '3px 10px',
                      borderRadius: '9999px',
                      fontSize: '11px',
                      fontWeight: 700,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <span
                      style={{
                        width: '7px',
                        height: '7px',
                        borderRadius: '50%',
                        background: response.mode === 'PROVIDER_LLM' ? '#16a34a' : '#d97706',
                      }}
                    />
                    {response.mode === 'PROVIDER_LLM'
                      ? 'Live AI Synthesis (Google Gemini)'
                      : response.status === 'DEGRADED_FALLBACK'
                      ? 'Deterministic Grounded Engine (Provider Unavailable)'
                      : 'Deterministic Grounded Engine (Configured)'}
                  </span>

                  <span
                    style={{
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      color: '#d6d3d1',
                      background: 'rgba(255,255,255,0.1)',
                      padding: '3px 8px',
                      borderRadius: '4px',
                    }}
                  >
                    Status: {response.status}
                  </span>
                </div>
              </div>

              {/* Engine Provenance Summary Bar */}
              <div
                style={{
                  padding: '8px 20px',
                  background: 'var(--stone-100)',
                  borderBottom: '1px solid var(--stone-200)',
                  fontSize: '11px',
                  color: 'var(--stone-600)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div>
                  <strong>Active Engine Provider:</strong> {response.provider}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span>
                    <strong>Sources Consulted:</strong> {response.sources_used.join(', ')}
                  </span>
                  <span>•</span>
                  <span>{response.timestamp}</span>
                </div>
              </div>

              {/* Main Analytical Body */}
              <div style={{ padding: '24px 28px' }}>
                {renderFormattedAnswer(response.answer)}

                {/* Grounded Database Evidence Section */}
                {response.evidence && response.evidence.length > 0 && (
                  <div
                    style={{
                      marginTop: '28px',
                      border: '1px solid var(--stone-200)',
                      borderRadius: '6px',
                      overflow: 'hidden',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setEvidenceExpanded(!evidenceExpanded)}
                      style={{
                        width: '100%',
                        padding: '10px 16px',
                        background: 'var(--bg-surface-subtle)',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: 'var(--stone-800)',
                        cursor: 'pointer',
                        borderBottom: evidenceExpanded ? '1px solid var(--stone-200)' : 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Database size={14} style={{ color: '#0f766e' }} />
                        <span>Supporting Grounded Database Evidence ({response.evidence.length} Records)</span>
                      </div>
                      {evidenceExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                    </button>

                    {evidenceExpanded && (
                      <div style={{ padding: '12px 16px', overflowX: 'auto', background: '#ffffff' }}>
                        {/* Provenance Legend */}
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '14px',
                            marginBottom: '10px',
                            fontSize: '11px',
                            color: 'var(--stone-600)',
                            background: '#fafaf9',
                            padding: '6px 10px',
                            borderRadius: '4px',
                            border: '1px solid #e7e5e4',
                          }}
                        >
                          <span style={{ fontWeight: 600 }}>Data Provenance Tags:</span>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <span style={{ background: '#ecfdf5', color: '#065f46', border: '1px solid #a7f3d0', padding: '1px 6px', borderRadius: '3px', fontSize: '10px', fontWeight: 700 }}>
                              IMPORTED
                            </span>
                            = Empirical Portal Observations
                          </span>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <span style={{ background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a', padding: '1px 6px', borderRadius: '3px', fontSize: '10px', fontWeight: 700 }}>
                              SYNTHETIC BASELINE
                            </span>
                            = Calibrated Pilot Baseline Data
                          </span>
                        </div>

                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11.5px', textAlign: 'left' }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid var(--stone-300)', color: 'var(--stone-600)' }}>
                              <th style={{ padding: '6px 8px' }}>Occupation Title &amp; NCO</th>
                              <th style={{ padding: '6px 8px' }}>District</th>
                              <th style={{ padding: '6px 8px' }}>Period</th>
                              <th style={{ padding: '6px 8px' }}>Observed Demand</th>
                              <th style={{ padding: '6px 8px' }}>Qualified Supply</th>
                              <th style={{ padding: '6px 8px' }}>Sanctioned Seats</th>
                              <th style={{ padding: '6px 8px' }}>Absolute Gap</th>
                              <th style={{ padding: '6px 8px' }}>Data Provenance</th>
                            </tr>
                          </thead>
                          <tbody>
                            {response.evidence.map((ev, idx) => {
                              const isImported = ev.data_status === 'IMPORTED' || ev.data_status.includes('IMPORTED');
                              const isShortage = (ev.absolute_gap || 0) > 0;
                              return (
                                <tr key={idx} style={{ borderBottom: '1px solid var(--stone-200)', background: idx % 2 === 0 ? '#ffffff' : '#fafaf9' }}>
                                  <td style={{ padding: '6px 8px' }}>
                                    <div style={{ fontWeight: 600, color: 'var(--stone-900)' }}>{ev.canonical_title}</div>
                                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--stone-500)' }}>
                                      {ev.nco_code}
                                    </div>
                                  </td>
                                  <td style={{ padding: '6px 8px' }}>{ev.district_code}</td>
                                  <td style={{ padding: '6px 8px' }}>{ev.reporting_period}</td>
                                  <td style={{ padding: '6px 8px', fontWeight: 600 }}>{ev.demand_value ?? '-'}</td>
                                  <td style={{ padding: '6px 8px' }}>{ev.supply_value ?? '-'}</td>
                                  <td style={{ padding: '6px 8px', color: 'var(--stone-600)' }}>{ev.training_seats ?? '-'}</td>
                                  <td style={{ padding: '6px 8px' }}>
                                    <span
                                      style={{
                                        fontWeight: 700,
                                        color: isShortage ? 'var(--shortage-rust)' : 'var(--balanced-green)',
                                      }}
                                    >
                                      {ev.absolute_gap !== null
                                        ? ev.absolute_gap > 0
                                          ? `+${ev.absolute_gap}`
                                          : `${ev.absolute_gap}`
                                        : '-'}
                                    </span>
                                  </td>
                                  <td style={{ padding: '6px 8px' }}>
                                    <span
                                      style={{
                                        display: 'inline-block',
                                        padding: '2px 6px',
                                        borderRadius: '3px',
                                        fontSize: '9.5px',
                                        fontWeight: 700,
                                        letterSpacing: '0.02em',
                                        background: isImported ? '#ecfdf5' : '#fffbeb',
                                        color: isImported ? '#065f46' : '#92400e',
                                        border: isImported ? '1px solid #a7f3d0' : '1px solid #fde68a',
                                      }}
                                    >
                                      {isImported ? 'IMPORTED (OBSERVED)' : 'SYNTHETIC BASELINE'}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* Methodological Limitations Section */}
                {response.limitations && response.limitations.length > 0 && (
                  <div
                    style={{
                      marginTop: '20px',
                      border: '1px solid #fef3c7',
                      background: '#fffbeb',
                      borderRadius: '6px',
                      overflow: 'hidden',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setLimitationsExpanded(!limitationsExpanded)}
                      style={{
                        width: '100%',
                        padding: '10px 16px',
                        background: 'transparent',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: '#92400e',
                        cursor: 'pointer',
                        borderBottom: limitationsExpanded ? '1px solid #fde68a' : 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <AlertTriangle size={14} style={{ color: '#d97706' }} />
                        <span>Methodological Limitations &amp; Quality Caveats ({response.limitations.length})</span>
                      </div>
                      {limitationsExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                    </button>

                    {limitationsExpanded && (
                      <div style={{ padding: '12px 16px', fontSize: '11.5px', color: '#78350f' }}>
                        <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                          {response.limitations.map((lim, idx) => (
                            <li key={idx} style={{ lineHeight: '1.5' }}>
                              {lim}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Official Institutional Disclaimer */}
                <div
                  style={{
                    marginTop: '24px',
                    padding: '12px 16px',
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    fontSize: '11px',
                    color: '#64748b',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    lineHeight: '1.5',
                  }}
                >
                  <Info size={15} style={{ color: '#0284c7', flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <strong>Decision Support Notice:</strong> {response.disclaimer}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
