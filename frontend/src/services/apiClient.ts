/**
 * LMIS Forecasting Engine — Typed Backend API Client
 * Conforms to LMIS Master R&D and AI Handoff specifications.
 * 
 * Provides unified, typed access to all FastAPI endpoints with:
 * - Configurable Base URL (VITE_API_BASE_URL)
 * - Explicit error handling (Network, Validation, Server errors)
 * - Clear data status classification (LIVE_BACKEND vs SYNTHETIC_DEMO)
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || (typeof window !== 'undefined' ? '' : 'http://127.0.0.1:8000');

import type { RecommendationListResponse, AiQueryRequest, AiQueryResponse } from '../types/lmis';

export interface ApiHealthResponse {
  status: string;
  version: string;
  app_name: string;
  database: string;
}

export interface BackendGapIndicator {
  nco_code: string;
  canonical_title: string;
  district_code: string;
  reporting_period: string;
  demand_value: number;
  qualified_supply_value: number;
  absolute_gap: number;
  gap_rate_pct: number | null;
  evidence_status: string;
  is_suitable_for_planning: boolean;
  data_status: string;
  limitations: string[];
}

export interface BackendGapDetailResponse {
  nco_code: string;
  canonical_title: string;
  division_code: string;
  division_title: string;
  district_code: string;
  reporting_period: string;
  demand_value: number;
  demand_source: string;
  demand_method: string;
  demand_status: string;
  supply_value: number;
  supply_source: string;
  supply_method: string;
  supply_status: string;
  absolute_gap: number;
  gap_rate_pct: number | null;
  evidence_status: string;
  is_suitable_for_planning: boolean;
  data_status: string;
  unresolved_postings_count: number;
  rejected_postings_count: number;
  sanctioned_training_seats: number | null;
  enrolled_students: number | null;
  completed_students: number | null;
  placed_students: number | null;
  placement_rate_pct: number | null;
  training_capacity_caveat: string;
  formula_used: string;
  limitations: string[];
}

export interface BackendAlertItem {
  alert_id: string;
  nco_code: string;
  canonical_title: string | null;
  district_code: string;
  reporting_period: string;
  alert_type: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  title: string;
  trigger_rule: string;
  evidence_summary: string;
  review_action_recommended: string;
  observed_demand: number | null;
  estimated_supply: number | null;
  absolute_gap: number | null;
  gap_rate_pct: number | null;
  threshold_type: string;
  triage_status?: string;
  triage_note?: string | null;
  data_status: string;
  limitations: string;
  created_at: string;
}

export interface BackendForecastResponse {
  nco_code: string;
  canonical_title: string | null;
  district_code: string;
  target_metric: string;
  horizon_periods: number;
  historical_series: {
    period: string;
    observed_value: number;
    source_system: string;
    data_status: string;
  }[];
  forecast_points: {
    period: string;
    step_ahead: number;
    forecast_value: number;
    lower_bound: number | null;
    upper_bound: number | null;
    confidence_level: number | null;
    is_projection: boolean;
    data_status?: string;
  }[];
  evaluation: {
    evaluation_status: 'EVALUATED' | 'INSUFFICIENT_DATA' | 'NOT_EVALUATED';
    baseline_model_name: string;
    candidate_model_name: string;
    selected_model_name: string;
    train_start_period: string | null;
    train_end_period: string | null;
    holdout_periods_count: number;
    total_historical_points: number;
    baseline_mae: number | null;
    candidate_mae: number | null;
    baseline_rmse: number | null;
    candidate_rmse: number | null;
    baseline_mape: number | null;
    candidate_mape: number | null;
    model_comparison_verdict: string;
    leakage_prevention_notice: string;
  };
  data_status: string;
  limitations: string[];
}

export interface BackendScenarioRequest {
  nco_code: string;
  district_code: string;
  reporting_period: string;
  baseline_gap: number;
  proposed_additional_seats: number;
  enrolment_rate_pct?: number;
  completion_rate_pct?: number;
  local_entry_rate_pct?: number;
  estimated_cost_per_seat_inr?: number;
  trainee_trainer_ratio?: number;
}

export interface BackendScenarioResponse {
  nco_code: string;
  canonical_title: string | null;
  district_code: string;
  reporting_period: string;
  baseline_gap: number;
  proposed_additional_seats: number;
  enrolment_rate_pct: number;
  completion_rate_pct: number;
  local_entry_rate_pct: number;
  effective_yield_per_seat: number;
  scenario_entrants: number;
  residual_gap: number;
  gap_reduction_pct: number;
  estimated_budget_inr: number;
  estimated_trainers_required: number;
  formula_used: string;
  calculation_steps: string[];
  is_scenario_only: boolean;
  policy_disclaimer: string;
  limitations: string[];
}

export interface BackendReviewQueueItem {
  id: number;
  raw_title: string;
  batch_id: string;
  district_code: string;
  source_system: string;
  suggested_nco_code: string | null;
  suggested_canonical_title: string | null;
  match_method: string;
  confidence_score: number;
  review_status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewer_notes: string | null;
  created_at: string;
}

export interface BackendValidationResult {
  is_valid: boolean;
  total_rows: number;
  valid_rows_count: number;
  invalid_rows_count: number;
  errors: { row_number: number; column_name: string; error_type: string; message: string; raw_value: string }[];
  summary: { source_system?: string; districts_found?: string[]; date_range?: string };
}

export interface BackendImportResult {
  batch_id: string;
  filename: string;
  status: string;
  uploaded_at: string;
  total_rows: number;
  imported_rows: number;
  rejected_rows: number;
  file_hash: string;
  proposals_created: number;
  message: string;
}

export interface BatchNormalizationResponse {
  batch_id: string;
  total_postings_processed: number;
  proposals_created: number;
  message: string;
}

export interface PipelineRecomputeResponse {
  batch_id?: string | null;
  total_approved_postings_aggregated: number;
  unresolved_postings_excluded: number;
  rejected_postings_excluded: number;
  observations_created_or_updated: number;
  forecasts_recomputed?: number;
  recommendations_generated?: number;
  alerts_evaluated: number;
  critical_alerts_count?: number;
  warning_alerts_count?: number;
  info_alerts_count?: number;
  message: string;
  timestamp: string;
}

export interface BackendConnectorMetadata {
  connector_id: string;
  connector_name: string;
  source_family: string;
  connection_status: string;
  auth_mechanism: string;
  is_live_connection: boolean;
  expected_schema: Record<string, string>;
  description: string;
  limitations_notice: string;
  verification_disclaimer: string;
}

export interface BackendAuditEvent {
  id: number;
  event_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  action_summary: string;
  details?: Record<string, unknown>;
  created_at: string;
}

export interface BackendExplainabilityDoc {
  title: string;
  primary_reference: string;
  mathematical_formula?: string;
  coverage_level?: string;
  assumptions?: string[];
  limitations?: string[];
  data_compatibility_rules?: string[];
  rule_hierarchy?: string[];
  archetypes?: string[];
}

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
      });

      if (!response.ok) {
        let errMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errData = await response.json();
          if (errData.detail) {
            errMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
          }
        } catch {
          if (response.status === 502) {
            errMessage = 'Service temporarily unavailable (HTTP 502 Bad Gateway). Unable to reach the backend intelligence engine. Please verify that the LMIS FastAPI backend server is running on http://127.0.0.1:8000.';
          } else if (response.status === 503) {
            errMessage = 'Service temporarily unavailable (HTTP 503). The intelligence engine is currently initializing or undergoing maintenance.';
          }
        }
        throw new Error(errMessage);
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
          throw new Error('Connection failed: Unable to communicate with the LMIS backend. Please verify that the FastAPI backend server is running on http://127.0.0.1:8000.', { cause: err });
        }
        throw err;
      }
      throw new Error('Unknown network error occurred while communicating with backend.', { cause: err });
    }

  }

  // Health
  async checkHealth(): Promise<ApiHealthResponse> {
    return this.request<ApiHealthResponse>('/api/health');
  }

  // Analytics Gaps
  async getGaps(districtCode?: string, reportingPeriod?: string): Promise<BackendGapIndicator[]> {
    const params = new URLSearchParams();
    if (districtCode && districtCode !== 'All Districts') {
      const code = districtCode === 'Pune' ? 'MH_PUN' : districtCode === 'Nashik' ? 'MH_NSK' : districtCode;
      params.append('district_code', code);
    }
    if (reportingPeriod) {
      params.append('reporting_period', reportingPeriod);
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<BackendGapIndicator[]>(`/api/analytics/gaps${query}`);
  }

  async getGapDetail(ncoCode: string, districtCode: string, reportingPeriod: string): Promise<BackendGapDetailResponse> {
    const params = new URLSearchParams({
      nco_code: ncoCode,
      district_code: districtCode,
      reporting_period: reportingPeriod,
    });
    return this.request<BackendGapDetailResponse>(`/api/analytics/gaps/detail?${params.toString()}`);
  }

  // Alerts
  async getAlerts(districtCode?: string, severity?: string, alertType?: string): Promise<BackendAlertItem[]> {
    const params = new URLSearchParams();
    if (districtCode && districtCode !== 'All Districts') {
      const code = districtCode === 'Pune' ? 'MH_PUN' : districtCode === 'Nashik' ? 'MH_NSK' : districtCode;
      params.append('district_code', code);
    }
    if (severity) params.append('severity', severity);
    if (alertType) params.append('alert_type', alertType);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<BackendAlertItem[]>(`/api/alerts${query}`);
  }

  async evaluateAlerts(): Promise<{ total_alerts_evaluated: number; message: string }> {
    return this.request('/api/alerts/evaluate', { method: 'POST' });
  }

  async updateAlertTriage(
    alertId: string,
    triageStatus: string,
    triageNote?: string,
    actor = 'PLANNING_OFFICER'
  ): Promise<BackendAlertItem> {
    return this.request<BackendAlertItem>(`/api/alerts/${encodeURIComponent(alertId)}/triage`, {
      method: 'PATCH',
      body: JSON.stringify({
        triage_status: triageStatus,
        triage_note: triageNote,
        actor,
      }),
    });
  }

  // Forecasting
  async getProjections(
    ncoCode: string,
    districtCode: string,
    targetMetric = 'DEMAND',
    horizon = 3
  ): Promise<BackendForecastResponse> {
    const params = new URLSearchParams({
      nco_code: ncoCode,
      district_code: districtCode,
      target_metric: targetMetric,
      horizon_periods: horizon.toString(),
    });
    return this.request<BackendForecastResponse>(`/api/forecasting/projections?${params.toString()}`);
  }

  async generateForecast(payload: {
    nco_code: string;
    district_code: string;
    target_metric: string;
    horizon_periods: number;
    holdout_periods?: number;
  }): Promise<BackendForecastResponse> {
    return this.request<BackendForecastResponse>('/api/forecasting/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getForecastEvaluations(districtCode?: string): Promise<Record<string, unknown>[]> {
    const params = new URLSearchParams();
    if (districtCode) params.append('district_code', districtCode);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<Record<string, unknown>[]>(`/api/forecasting/evaluations${query}`);
  }

  // Scenario Planner
  async calculateScenario(payload: BackendScenarioRequest): Promise<BackendScenarioResponse> {
    return this.request<BackendScenarioResponse>('/api/scenarios/calculate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getScenarioDefaults(): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>('/api/scenarios/defaults');
  }

  // Normalization Review Queue
  async getReviewQueue(status = 'PENDING'): Promise<BackendReviewQueueItem[]> {
    return this.request<BackendReviewQueueItem[]>(`/api/normalization/human-review-queue?review_status=${status}`);
  }

  async submitReviewDecision(
    reviewId: number,
    decision: 'APPROVED' | 'REJECTED',
    notes = '',
    overrideNcoCode?: string
  ): Promise<Record<string, unknown>> {
    const params = new URLSearchParams({ decision, reviewer_notes: notes });
    if (overrideNcoCode) params.append('override_nco_code', overrideNcoCode);
    return this.request<Record<string, unknown>>(`/api/normalization/human-review/${reviewId}?${params.toString()}`, {
      method: 'POST',
    });
  }

  // Ingestion
  async validateCsv(file: File): Promise<BackendValidationResult> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/api/ingestion/validate`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Validation failed');
    }
    return response.json();
  }

  async importCsv(file: File, sourceSystem = 'NCS_FEED'): Promise<BackendImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/api/ingestion/import?source_system=${sourceSystem}`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Import failed');
    }
    return response.json();
  }

  async processBatch(batchId: string): Promise<BatchNormalizationResponse> {
    return this.request<BatchNormalizationResponse>(`/api/normalization/process-batch/${encodeURIComponent(batchId)}`, {
      method: 'POST',
    });
  }

  async recomputePipeline(batchId?: string): Promise<PipelineRecomputeResponse> {
    const query = batchId ? `?batch_id=${encodeURIComponent(batchId)}` : '';
    return this.request<PipelineRecomputeResponse>(`/api/analytics/recompute-pipeline${query}`, {
      method: 'POST',
    });
  }

  async getImportBatches(): Promise<Record<string, unknown>[]> {
    return this.request<Record<string, unknown>[]>('/api/ingestion/batches');
  }

  async getRecommendations(params?: {
    nco_code?: string;
    district_code?: string;
    recommendation_type?: string;
    priority?: string;
  }): Promise<RecommendationListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.nco_code) searchParams.append('nco_code', params.nco_code);
    if (params?.district_code) searchParams.append('district_code', params.district_code);
    if (params?.recommendation_type) searchParams.append('recommendation_type', params.recommendation_type);
    if (params?.priority) searchParams.append('priority', params.priority);
    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return this.request<RecommendationListResponse>(`/api/recommendations${query}`);
  }

  async evaluateRecommendations(): Promise<RecommendationListResponse> {
    return this.request<RecommendationListResponse>('/api/recommendations/evaluate', {
      method: 'POST',
    });
  }

  async getConnectors(): Promise<BackendConnectorMetadata[]> {
    return this.request<BackendConnectorMetadata[]>('/api/ingestion/connectors');
  }

  async getAuditLogs(eventType?: string, limit = 50): Promise<BackendAuditEvent[]> {
    const params = new URLSearchParams();
    if (eventType) params.append('event_type', eventType);
    params.append('limit', limit.toString());
    return this.request<BackendAuditEvent[]>(`/api/governance/audit-logs?${params.toString()}`);
  }

  async getExplainability(topic: string): Promise<BackendExplainabilityDoc> {
    return this.request<BackendExplainabilityDoc>(`/api/governance/explainability/${encodeURIComponent(topic)}`);
  }

  // AI Assistant
  async askAssistant(payload: AiQueryRequest): Promise<AiQueryResponse> {
    return this.request<AiQueryResponse>('/api/ai/ask', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const apiClient = new ApiClient();

