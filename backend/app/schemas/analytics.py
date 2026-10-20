"""Pydantic schemas for demand observations, supply estimates, training capacity, and gap analytics."""

from pydantic import BaseModel, Field

class DemandObservationCreate(BaseModel):
    nco_code: str = Field(..., description="Canonical NCO-2015 code (e.g. 7421.0301)")
    district_code: str = Field(..., description="Standard district code (e.g. MH_PUN, MH_NSK)")
    reporting_period: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Reporting period (YYYY-MM)")
    demand_value: int = Field(..., ge=0, description="Observed hiring volume / postings signal (>= 0)")
    unit: str = Field("OBSERVED_POSTINGS", description="Unit of measurement")
    source_system: str = Field(..., description="Ingestion source channel (e.g. NCS_FEED, PORTAL_SCRAPE)")
    observation_method: str = Field("DIRECT_OBSERVATION", description="Methodology used to derive signal")
    data_status: str = Field("PILOT_BASELINE", description="'PILOT_BASELINE', 'SYNTHETIC_DEMO', or 'REAL_PUBLIC_DATA'")
    limitations: str | None = Field(None, description="Known caveats or coverage limitations")

class DemandObservationItem(BaseModel):
    id: int
    nco_code: str
    canonical_title: str | None = None
    district_code: str
    reporting_period: str
    demand_value: int
    unit: str
    source_system: str
    observation_method: str
    data_status: str
    unresolved_postings_count: int = 0
    rejected_postings_count: int = 0
    limitations: str | None = None
    created_at: str

class QualifiedSupplyEstimateCreate(BaseModel):
    nco_code: str = Field(..., description="Canonical NCO-2015 code (e.g. 7421.0301)")
    district_code: str = Field(..., description="Standard district code (e.g. MH_PUN, MH_NSK)")
    reporting_period: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Reporting period (YYYY-MM)")
    supply_value: int = Field(..., ge=0, description="Estimated pool of plausibly qualified workers (>= 0)")
    unit: str = Field("QUALIFIED_WORKERS", description="Unit of measurement")
    source_name: str = Field(..., description="Originating agency or survey (e.g. NCVET_COMPLETIONS_SYNTHESIS)")
    estimation_method: str = Field("QUALIFIED_COHORT_SYNTHESIS", description="Methodology applied")
    data_status: str = Field("PILOT_BASELINE", description="'PILOT_BASELINE', 'SYNTHETIC_DEMO', or 'REAL_PUBLIC_DATA'")
    confidence_interval_low: int | None = Field(None, ge=0)
    confidence_interval_high: int | None = Field(None, ge=0)
    limitations: str | None = Field(None, description="Known caveats or methodology limitations")

class QualifiedSupplyEstimateItem(BaseModel):
    id: int
    nco_code: str
    canonical_title: str | None = None
    district_code: str
    reporting_period: str
    supply_value: int
    unit: str
    source_name: str
    estimation_method: str
    data_status: str
    confidence_interval_low: int | None = None
    confidence_interval_high: int | None = None
    limitations: str | None = None
    created_at: str

class TrainingCapacityCreate(BaseModel):
    nco_code: str
    district_code: str
    reporting_period: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    sanctioned_seats: int = Field(..., ge=0, description="Institutional seat capacity (NOT active supply)")
    enrolled_students: int | None = Field(None, ge=0)
    completed_students: int | None = Field(None, ge=0)
    placed_students: int | None = Field(None, ge=0)
    placement_rate_pct: float | None = Field(None, ge=0.0, le=100.0)
    source_system: str
    data_status: str = "PILOT_BASELINE"
    limitations: str | None = None

class TrainingCapacityItem(BaseModel):
    id: int
    nco_code: str
    canonical_title: str | None = None
    district_code: str
    reporting_period: str
    sanctioned_seats: int
    enrolled_students: int | None = None
    completed_students: int | None = None
    placed_students: int | None = None
    placement_rate_pct: float | None = None
    source_system: str
    data_status: str
    limitations: str | None = None
    created_at: str

class GapIndicatorSummary(BaseModel):
    nco_code: str
    canonical_title: str
    district_code: str
    reporting_period: str
    demand_value: int | None = None
    qualified_supply_value: int | None = None
    absolute_gap: int | None = None
    gap_rate_pct: float | None = None
    evidence_status: str = Field(..., description="'CALCULATED', 'MISSING_SUPPLY', 'MISSING_DEMAND', 'INCOMPATIBLE_PERIOD_OR_GEOGRAPHY', or 'INSUFFICIENT_EVIDENCE'")
    data_status: str = Field(..., description="Combined provenance status (e.g. 'PILOT_BASELINE', 'SYNTHETIC_DEMO')")
    is_suitable_for_planning: bool = Field(..., description="Whether evidence meets criteria for policy use")

class GapDetailAuditResponse(BaseModel):
    nco_code: str
    canonical_title: str
    division_code: str
    division_title: str
    district_code: str
    reporting_period: str

    # Demand Evidence
    demand_value: int | None = None
    demand_unit: str | None = None
    demand_source: str | None = None
    demand_method: str | None = None
    demand_status: str | None = None
    unresolved_postings_count: int = 0
    rejected_postings_count: int = 0

    # Supply Evidence
    supply_value: int | None = None
    supply_unit: str | None = None
    supply_source: str | None = None
    supply_method: str | None = None
    supply_status: str | None = None
    confidence_interval_low: int | None = None
    confidence_interval_high: int | None = None

    # Institutional Capacity (Explicitly Separated from Supply)
    sanctioned_training_seats: int | None = None
    training_capacity_caveat: str | None = None

    # Gap Calculation Results
    absolute_gap: int | None = None
    gap_rate_pct: float | None = None
    zero_demand_note: str | None = None
    formula_used: str

    # Evidence Quality & Governance
    evidence_status: str
    combined_data_status: str
    limitations: list[str]
    is_suitable_for_planning: bool
    transparency_notice: str

class DemandAggregationResponse(BaseModel):
    total_approved_postings_aggregated: int
    unresolved_postings_excluded: int
    rejected_postings_excluded: int
    observations_created_or_updated: int
    message: str


class PipelineRecomputeResponse(BaseModel):
    """Response returned when the entire intelligence pipeline is recomputed."""

    total_approved_postings_aggregated: int = Field(
        ...,
        description="Number of vacancies from approved postings contributed to confirmed demand",
    )
    unresolved_postings_excluded: int = Field(
        ...,
        description="Number of unapproved postings excluded pending human review",
    )
    rejected_postings_excluded: int = Field(
        ...,
        description="Number of rejected postings excluded from confirmed demand",
    )
    observations_created_or_updated: int = Field(
        ...,
        description="Number of demand observation records created or updated",
    )
    forecasts_recomputed: int = Field(
        0,
        description="Number of occupation forecasts automatically recomputed",
    )
    recommendations_generated: int = Field(
        0,
        description="Number of evidence-backed policy recommendations generated",
    )
    alerts_evaluated: int = Field(
        ...,
        description="Total early-warning alerts generated or updated across all occupations",
    )
    critical_alerts_count: int = Field(..., description="Count of CRITICAL severity alerts")
    warning_alerts_count: int = Field(..., description="Count of WARNING severity alerts")
    info_alerts_count: int = Field(..., description="Count of INFO severity alerts")
    message: str = Field(..., description="Summary execution message")
