import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Sparkles,
  X,
  Send,
  Database,
  AlertCircle,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';
import { apiClient } from '../../services/apiClient';
import type { AiQueryResponse, PilotDistrict } from '../../types/lmis';

import { RotateCcw } from 'lucide-react';

interface AiAssistantDrawerProps {
  selectedDistrict: PilotDistrict;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  response?: AiQueryResponse;
  timestamp: string;
}

const SAMPLE_QUESTIONS = [
  'Which occupations have the largest skill shortages?',
  'Explain the forecast for an occupation.',
  'Which alerts need attention?',
  'What training interventions could address the identified gaps?',
  'What data limitations affect these findings?',
];

export const AiAssistantDrawer: React.FC<AiAssistantDrawerProps> = ({ selectedDistrict }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [queryInput, setQueryInput] = useState('');
  const [lastAttemptedQuery, setLastAttemptedQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [emptyInputWarning, setEmptyInputWarning] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});
  const [expandedLimitations, setExpandedLimitations] = useState<Record<string, boolean>>({});
  const msgCounterRef = useRef(1);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text:
        'Welcome to the LMIS Labour Market Intelligence Assistant. ' +
        'Ask analytical questions regarding demand-supply gaps, qualified workforce estimates, ' +
        'sanctioned training seats, forecast projections, early warning alerts, and policy interventions. ' +
        'All responses are strictly grounded in verified analytical models and database records (read-only decision support).',
      timestamp: 'Session Start',
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const toggleEvidence = (msgId: string) => {
    setExpandedEvidence((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const toggleLimitations = (msgId: string) => {
    setExpandedLimitations((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleSend = useCallback(async (questionToSend?: string) => {
    const q = (questionToSend !== undefined ? questionToSend : queryInput).trim();
    if (!q) {
      setEmptyInputWarning(true);
      return;
    }
    if (isLoading) return;

    setEmptyInputWarning(false);
    setErrorMessage(null);
    setLastAttemptedQuery(q);
    setQueryInput('');

    msgCounterRef.current += 1;
    const userMsgId = `user-msg-${msgCounterRef.current}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: q,
      timestamp: 'Just now',
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const districtCode =
        selectedDistrict === 'Pune' ? 'MH_PUN' : selectedDistrict === 'Nashik' ? 'MH_NSK' : undefined;

      const response = await apiClient.askAssistant({
        query: q,
        district_code: districtCode,
      });

      msgCounterRef.current += 1;
      const asstMsgId = `asst-msg-${msgCounterRef.current}`;
      const assistantMsg: ChatMessage = {
        id: asstMsgId,
        sender: 'assistant',
        text: response.answer,
        response,
        timestamp: 'Just now',
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errText = err instanceof Error ? err.message : 'Failed to query LMIS intelligence assistant.';
      setErrorMessage(errText);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, queryInput, selectedDistrict]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 999,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'linear-gradient(135deg, #c2410c 0%, #9a3412 100%)',
            color: '#ffffff',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '9999px',
            padding: '12px 20px',
            fontSize: '13px',
            fontWeight: 700,
            letterSpacing: '0.02em',
            boxShadow: '0 10px 25px -5px rgba(194, 65, 12, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
            cursor: 'pointer',
            transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 14px 28px -5px rgba(194, 65, 12, 0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow =
              '0 10px 25px -5px rgba(194, 65, 12, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.1)';
          }}
          aria-label="Open LMIS AI Labour Market Intelligence Assistant"
        >
          <Sparkles size={16} style={{ color: '#fed7aa' }} />
          <span>AI Intelligence Assistant</span>
          <span
            style={{
              background: 'rgba(255,255,255,0.25)',
              fontSize: '10px',
              padding: '2px 6px',
              borderRadius: '4px',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            Live
          </span>
        </button>
      )}

      {/* Floating Assistant Drawer / Dialog */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="LMIS AI Assistant Dialogue"
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            width: '450px',
            maxWidth: 'calc(100vw - 32px)',
            height: '620px',
            maxHeight: 'calc(100vh - 48px)',
            background: '#ffffff',
            borderRadius: '14px',
            border: '1px solid #e7e5e4',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            style={{
              background: 'linear-gradient(to right, #1c1917, #292524)',
              color: '#ffffff',
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '2px solid #c2410c',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  background: 'rgba(194, 65, 12, 0.25)',
                  border: '1px solid #c2410c',
                  padding: '6px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Sparkles size={16} style={{ color: '#fed7aa' }} />
              </div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.01em' }}>
                  LMIS Intelligence Assistant
                </div>
                <div style={{ fontSize: '11px', color: '#a8a29e', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>Grounded Decision Support</span>
                  <span>•</span>
                  <span>Read-Only Engine</span>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setIsOpen(false)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#a8a29e',
                cursor: 'pointer',
                padding: '4px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Close Assistant"
              aria-label="Close Assistant"
            >
              <X size={18} />
            </button>
          </div>

          {/* District Scope Bar */}
          <div
            style={{
              background: '#f5f5f4',
              padding: '6px 14px',
              fontSize: '11px',
              color: '#57534e',
              borderBottom: '1px solid #e7e5e4',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={13} style={{ color: '#0f766e' }} />
              <span>
                Scope:{' '}
                <strong>
                  {selectedDistrict === 'All Districts'
                    ? 'All Pilot Districts (Pune & Nashik)'
                    : `${selectedDistrict} District`}
                </strong>
              </span>
            </div>
            <span
              style={{
                background: '#e0f2fe',
                color: '#0369a1',
                padding: '1px 6px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 600,
              }}
            >
              DB GROUNDED
            </span>
          </div>

          {/* Messages Scroll Area */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              background: '#fafaf9',
            }}
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                {/* Sender badge & timestamp */}
                <div
                  style={{
                    fontSize: '10px',
                    color: '#a8a29e',
                    marginBottom: '4px',
                    padding: '0 4px',
                  }}
                >
                  {msg.sender === 'user' ? 'You' : 'LMIS AI Assistant'} • {msg.timestamp}
                </div>

                {/* Message Bubble */}
                <div
                  style={{
                    maxWidth: '92%',
                    padding: '12px 14px',
                    borderRadius:
                      msg.sender === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                    background: msg.sender === 'user' ? '#c2410c' : '#ffffff',
                    color: msg.sender === 'user' ? '#ffffff' : '#1c1917',
                    border: msg.sender === 'user' ? 'none' : '1px solid #e7e5e4',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    fontSize: '12.5px',
                    lineHeight: '1.55',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {msg.text}

                  {/* Assistant Response Metadata and Accordions */}
                  {msg.response && (
                    <div
                      style={{
                        marginTop: '12px',
                        paddingTop: '10px',
                        borderTop: '1px solid #f5f5f4',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      {/* Provider mode pill */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '10.5px',
                        }}
                      >
                        <span
                          style={{
                            background: msg.response.mode === 'PROVIDER_LLM' ? '#dcfce7' : '#fef3c7',
                            color: msg.response.mode === 'PROVIDER_LLM' ? '#166534' : '#92400e',
                            padding: '2px 8px',
                            borderRadius: '9999px',
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span
                            style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              background: msg.response.mode === 'PROVIDER_LLM' ? '#16a34a' : '#d97706',
                            }}
                          />
                          {msg.response.mode === 'PROVIDER_LLM' ? 'Gemini Live Synthesis' : 'Rule-Based Engine'}
                        </span>

                        <span style={{ color: '#78716c', fontSize: '10px' }}>
                          {msg.response.provider}
                        </span>
                      </div>

                      {/* Evidence Dropdown */}
                      {msg.response.evidence.length > 0 && (
                        <div
                          style={{
                            background: '#f8fafc',
                            border: '1px solid #e2e8f0',
                            borderRadius: '6px',
                            overflow: 'hidden',
                          }}
                        >
                          <button
                            type="button"
                            onClick={() => toggleEvidence(msg.id)}
                            style={{
                              width: '100%',
                              padding: '6px 10px',
                              background: 'transparent',
                              border: 'none',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              fontSize: '11px',
                              fontWeight: 600,
                              color: '#334155',
                              cursor: 'pointer',
                            }}
                          >
                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <Database size={12} style={{ color: '#0f766e' }} />
                              Grounded Database Records ({msg.response.evidence.length})
                            </span>
                            {expandedEvidence[msg.id] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                          </button>

                          {expandedEvidence[msg.id] && (
                            <div style={{ padding: '8px 10px', borderTop: '1px solid #e2e8f0', fontSize: '10.5px' }}>
                              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                  <tr style={{ color: '#64748b', borderBottom: '1px solid #cbd5e1' }}>
                                    <th style={{ padding: '3px 0' }}>Occupation</th>
                                    <th>Dist</th>
                                    <th>Demand</th>
                                    <th>Supply</th>
                                    <th>Gap</th>
                                    <th>Data Status</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {msg.response.evidence.map((ev, idx) => {
                                    const isImported = ev.data_status === 'IMPORTED' || ev.data_status.includes('IMPORTED');
                                    return (
                                      <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '4px 0', fontWeight: 600 }}>{ev.canonical_title}</td>
                                        <td>{ev.district_code}</td>
                                        <td>{ev.demand_value ?? '-'}</td>
                                        <td>{ev.supply_value ?? '-'}</td>
                                        <td
                                          style={{
                                            fontWeight: 700,
                                            color: (ev.absolute_gap || 0) > 0 ? '#b91c1c' : '#047857',
                                          }}
                                        >
                                          {(ev.absolute_gap || 0) > 0 ? `+${ev.absolute_gap}` : ev.absolute_gap}
                                        </td>
                                        <td>
                                          <span
                                            style={{
                                              fontSize: '9px',
                                              fontWeight: 700,
                                              padding: '1px 5px',
                                              borderRadius: '3px',
                                              background: isImported ? '#ecfdf5' : '#fffbeb',
                                              color: isImported ? '#065f46' : '#92400e',
                                              border: isImported ? '1px solid #a7f3d0' : '1px solid #fde68a',
                                            }}
                                          >
                                            {isImported ? 'IMPORTED' : 'DEMO'}
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

                      {/* Limitations Dropdown */}
                      {msg.response.limitations.length > 0 && (
                        <div
                          style={{
                            background: '#fffbeb',
                            border: '1px solid #fef3c7',
                            borderRadius: '6px',
                            overflow: 'hidden',
                          }}
                        >
                          <button
                            type="button"
                            onClick={() => toggleLimitations(msg.id)}
                            style={{
                              width: '100%',
                              padding: '6px 10px',
                              background: 'transparent',
                              border: 'none',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              fontSize: '11px',
                              fontWeight: 600,
                              color: '#92400e',
                              cursor: 'pointer',
                            }}
                          >
                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <AlertCircle size={12} style={{ color: '#d97706' }} />
                              Methodological Limitations &amp; Caveats
                            </span>
                            {expandedLimitations[msg.id] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                          </button>

                          {expandedLimitations[msg.id] && (
                            <div
                              style={{
                                padding: '8px 10px',
                                borderTop: '1px solid #fef3c7',
                                fontSize: '10.5px',
                                color: '#78350f',
                              }}
                            >
                              <ul style={{ margin: 0, paddingLeft: '16px' }}>
                                {msg.response.limitations.map((lim, idx) => (
                                  <li key={idx} style={{ marginBottom: '3px' }}>
                                    {lim}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Institutional Disclaimer */}
                      <div
                        style={{
                          fontSize: '9.5px',
                          color: '#a8a29e',
                          fontStyle: 'italic',
                          marginTop: '2px',
                        }}
                      >
                        {msg.response.disclaimer}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#78716c', fontSize: '12px' }}>
                <Loader2 size={15} className="spinner" style={{ animation: 'spin 1s linear infinite' }} />
                <span>Retrieving verified LMIS records &amp; synthesizing analysis...</span>
              </div>
            )}

            {/* Error Banner with Retry */}
            {errorMessage && (
              <div
                style={{
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  color: '#991b1b',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '11.5px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertCircle size={14} style={{ flexShrink: 0 }} />
                  <span>{errorMessage}</span>
                </div>
                {lastAttemptedQuery && (
                  <button
                    type="button"
                    onClick={() => handleSend(lastAttemptedQuery)}
                    style={{
                      background: '#ffffff',
                      border: '1px solid #fca5a5',
                      borderRadius: '4px',
                      padding: '2px 8px',
                      fontSize: '10.5px',
                      fontWeight: 600,
                      color: '#991b1b',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      flexShrink: 0,
                    }}
                  >
                    <RotateCcw size={11} /> Retry
                  </button>
                )}
              </div>
            )}

            {/* Empty Input Warning */}
            {emptyInputWarning && (
              <div
                style={{
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  color: '#991b1b',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <AlertCircle size={13} />
                <span>Please enter a question or select a prompt below.</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompt Chips */}
          <div
            style={{
              padding: '8px 12px',
              background: '#f5f5f4',
              borderTop: '1px solid #e7e5e4',
              display: 'flex',
              gap: '6px',
              overflowX: 'auto',
              whiteSpace: 'nowrap',
            }}
          >
            {SAMPLE_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(q)}
                disabled={isLoading}
                style={{
                  background: '#ffffff',
                  border: '1px solid #d6d3d1',
                  borderRadius: '9999px',
                  padding: '4px 10px',
                  fontSize: '11px',
                  color: '#44403c',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  flexShrink: 0,
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.borderColor = '#c2410c';
                    e.currentTarget.style.color = '#c2410c';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#d6d3d1';
                  e.currentTarget.style.color = '#44403c';
                }}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <div
            style={{
              padding: '12px 14px',
              background: '#ffffff',
              borderTop: '1px solid #e7e5e4',
              display: 'flex',
              gap: '8px',
              alignItems: 'center',
            }}
          >
            <input
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask LMIS Assistant (e.g. 'Shortages in Pune')..."
              disabled={isLoading}
              style={{
                flex: 1,
                padding: '9px 12px',
                borderRadius: '8px',
                border: '1px solid #d6d3d1',
                fontSize: '12.5px',
                outline: 'none',
                fontFamily: 'inherit',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#c2410c';
                e.currentTarget.style.boxShadow = '0 0 0 2px rgba(194, 65, 12, 0.15)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = '#d6d3d1';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />

            <button
              type="button"
              onClick={() => handleSend()}
              disabled={isLoading || !queryInput.trim()}
              style={{
                background: queryInput.trim() && !isLoading ? '#c2410c' : '#e7e5e4',
                color: queryInput.trim() && !isLoading ? '#ffffff' : '#a8a29e',
                border: 'none',
                borderRadius: '8px',
                padding: '9px 14px',
                cursor: queryInput.trim() && !isLoading ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease',
              }}
              title="Submit Query"
              aria-label="Submit Query"
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};
