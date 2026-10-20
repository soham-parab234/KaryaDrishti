/**
 * LMIS Forecasting Engine — TypeScript Type Definitions
 * Source of truth: LMIS Master R&D & AI Handoff Specifications
 *
 * Domain Guardrails:
 * 1. Documented demand signals are NOT total vacancies.
 * 2. Qualified supply is NOT raw registrations (e-Shram) or training capacity.
 * 3. Institutional training seats represent capacity, not currently available workers.
 * 4. Forecast evaluations are calculated from actual time series or marked 'Not evaluated / Insufficient evidence'.
 * 5. All baseline demonstration figures are explicitly labeled SYNTHETIC BASELINE data.
 */

export type DataStatusLabel = 'REAL PUBLIC DATA' | 'IMPORTED' | 'SYNTHETIC DEMO' | 'SYNTHETIC BASELINE' | 'PLANNED';

export type RiskLevel =
  | 'CRITICAL_SHORTAGE'
  | 'MODERATE_SHORTAGE'
  | 'BALANCED'
  | 'POTENTIAL_OVERSUPPLY'
  | 'INSUFFICIENT_DATA';

export type AlertType =
  | 'SHORTAGE_RISK'
  | 'OVERSUPPLY_RISK'
  | 'PROJECTED_SHORTAGE_RISK'
  | 'PROJECTED_OVERSUPPLY_RISK'
  | 'EMERGING_DEMAND'
  | 'DATA_WARNING'
  | 'DATA_QUALITY_WARNING';

export type AlertSeverity = 'HIGH' | 'MEDIUM' | 'LOW' | 'WARNING';

export type AlertTriageStatus = 'NEW' | 'ACKNOWLEDGED' | 'ESCALATED' | 'VERIFICATION_REQUESTED';

export type Sector =
  | 'Clean Tech & Renewable Energy'
  | 'Advanced Manufacturing'
  | 'IT & IT-Enabled Services';

export type PilotDistrict = 'Pune' | 'Nashik' | 'All Districts';

export type NavigationView = 'overview' | 'occupations' | 'forecasts' | 'scenarios' | 'reports' | 'assistant';

export interface OccupationSummary {
  id: string;
  ncoCode: string; // NCO-2015 code (e.g. 7421.0301)
  ncoDivision: string; // e.g. "7 - Craft and Related Trades Workers"
  canonicalTitle: string;
  sector: Sector;
  district: 'Pune' | 'Nashik';
  nsqfLevel: number;
  documentedDemand: number; // Observed postings / employer signals
  qualifiedSupply: number; // Estimated pool of plausibly qualified workers
  trainingCapacity: number; // Sanctioned training seats (NOT active supply)
  enrolledStudents: number;
  lastYearCompletions: number;
  certifiedWorkers: number;
  reportedPlacementRate: number; // % placed according to tracking records
  absoluteGap: number; // Demand - Supply (positive = shortage, negative = surplus)
  gapRate: number | null; // (Demand - Supply) / Demand * 100 (null if demand <= 0)
  riskLevel: RiskLevel;
  sourceStatus: DataStatusLabel;
  lastUpdated: string;
  mappingConfidence: number; // 0 - 100%
  aliases: string[]; // Known portal title aliases mapped to this code
  taskDescription: string;
  caveat: string;
  monthlyHistory: { period: string; demand: number; supply: number }[];
}

export interface MonthlyTrendData {
  period: string;
  documentedDemand: number;
  qualifiedSupply: number;
  trainingCapacity?: number;
  projectedDemandBaseline?: number;
  projectedSupplyBaseline?: number;
  isForecast?: boolean;
  uncertaintyLower?: number;
  uncertaintyUpper?: number;
}

export interface EarlyWarningSignal {
  id: string;
  alertType: AlertType;
  severity: AlertSeverity;
  triageStatus: AlertTriageStatus;
  occupation: string;
  ncoCode: string;
  district: string;
  projectedGap: number;
  gapRate: number | null;
  evidenceSummary: string;
  uncertaintyNote: string;
  recommendedAction: string;
  sourceStatus: DataStatusLabel;
  detectedAt: string;
  triageNote?: string;
}

export interface ForecastModelEvaluation {
  modelName: string;
  modelType: 'BASELINE_MA' | 'NAIVE_LAST' | 'LINEAR_DRIFT' | 'CANDIDATE_ETS' | 'CANDIDATE_ARIMA';
  targetSeries: string;
  evaluationStatus: 'EVALUATED' | 'INSUFFICIENT_DATA' | 'NOT_EVALUATED';
  holdoutPeriodsCount: number;
  calculatedMae: number | null;
  calculatedRmse: number | null;
  calculatedMape: number | null;
  evaluationWindow: string;
  modelVerdict: string;
  modelSelectionVerdict?: string;
  caveat: string;
}

export interface ScenarioParameters {
  targetOccupationId: string;
  proposedSeats: number;
  enrolmentRate: number; // 0 - 100
  completionRate: number; // 0 - 100
  localEntryRate: number; // 0 - 100
  trainerRatioRequired: number; // e.g. 20 seats per certified instructor
  unitCostPerSeat: number; // INR cost per seat
}

export interface ScenarioResult {
  yieldPerSeat: number;
  expectedQualifiedEntrants: number;
  baselineGap: number;
  residualGap: number;
  gapReductionPercent: number;
  instructorsNeeded: number;
  estimatedBudget: number;
  feasibilityWarning?: string;
}

export interface DataSourceProvenance {
  id: string;
  dataFamily: string;
  referenceSource: string;
  currentStatus: DataStatusLabel;
  geographyScope: string;
  updateFrequency: string;
  lastObserved: string;
  recordCount: string;
  limitationNotice: string;
}

export interface IngestionSchemaField {
  fieldName: string;
  dataType: string;
  required: boolean;
  validationRule: string;
  description: string;
}

export interface IngestionBatchRecord {
  batchId: string;
  sourceName: string;
  uploadedAt: string;
  totalRows: number;
  validRows: number;
  rejectedRows: number;
  status: 'COMPLETED' | 'VALIDATION_FAILED' | 'WARNING';
  errorSummary: string;
}

export interface GlobalFilterState {
  district: PilotDistrict;
  sector: Sector | 'All Sectors';
  period: string;
}

export interface PolicyRecommendation {
  recommendation_id: string;
  nco_code: string;
  canonical_title?: string;
  district_code: string;
  reporting_period: string;
  recommendation_type:
    | 'TRAINING_CAPACITY_EXPANSION'
    | 'CURRICULUM_MODERNIZATION_OR_PIVOT'
    | 'APPRENTICESHIP_INDUSTRY_TIE_UP'
    | 'DATA_COLLECTION_AUDIT';
  action_title: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  rationale: string;
  evidence_sources: Record<string, unknown>;
  proposed_seat_adjustment: number;
  target_horizon_months: number;
  expected_impact_summary: string;
  feasibility_score: number;
  data_status: string;
  limitations: string[];
  created_at?: string;
}

export interface RecommendationListResponse {
  total_recommendations: number;
  expansion_count: number;
  curriculum_pivot_count: number;
  apprenticeship_count: number;
  data_audit_count: number;
  items: PolicyRecommendation[];
}

export interface AiEvidenceItem {
  nco_code: string;
  canonical_title: string;
  district_code: string;
  reporting_period: string;
  demand_value: number | null;
  supply_value: number | null;
  absolute_gap: number | null;
  gap_rate_pct: number | null;
  training_seats: number | null;
  placement_rate_pct: number | null;
  risk_level: string | null;
  data_status: string;
}

export interface AiQueryRequest {
  query: string;
  district_code?: string;
  occupation_code?: string;
  sector?: string;
}

export interface AiQueryResponse {
  query: string;
  answer: string;
  mode: 'PROVIDER_LLM' | 'RULE_BASED_FALLBACK';
  provider: string;
  status: 'SUCCESS' | 'DEGRADED_FALLBACK' | 'INSUFFICIENT_DATA';
  evidence: AiEvidenceItem[];
  limitations: string[];
  sources_used: string[];
  disclaimer: string;
  timestamp: string;
}
