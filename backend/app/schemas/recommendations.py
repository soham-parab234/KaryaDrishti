"""Pydantic schemas for Policy and Workforce Recommendations (Phase 10: Decision Intelligence)."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PolicyRecommendationItem(BaseModel):
    """Structured representation of an evidence-backed policy recommendation."""

    model_config = ConfigDict(from_attributes=True)

    recommendation_id: str = Field(..., description="Unique deterministic identifier for recommendation")
    nco_code: str = Field(..., description="Target National Classification of Occupations 2015 code")
    canonical_title: str | None = Field(None, description="Official title for occupation")
    district_code: str = Field(..., description="District code (e.g. MH-PUN)")
    reporting_period: str = Field(..., description="Reporting period (YYYY-MM)")
    recommendation_type: str = Field(
        ...,
        description="Archetype: TRAINING_CAPACITY_EXPANSION, CURRICULUM_MODERNIZATION_OR_PIVOT, APPRENTICESHIP_INDUSTRY_TIE_UP, DATA_COLLECTION_AUDIT"
    )
    action_title: str = Field(..., description="Actionable title for policymaker review")
    priority: str = Field("MEDIUM", description="Priority level: HIGH, MEDIUM, LOW")
    rationale: str = Field(..., description="Mathematical and evidence-based rationale")
    evidence_sources: Any = Field(..., description="Detailed evidentiary metrics: gap, forecast, capacity")
    proposed_seat_adjustment: int = Field(0, description="Recommended annual training seat change")
    target_horizon_months: int = Field(12, description="Implementation time horizon in months")
    expected_impact_summary: str = Field(..., description="Quantified expectation on mismatch ratio or supply")
    feasibility_score: float = Field(..., description="Feasibility confidence metric between 0.0 and 1.0")
    data_status: str = Field(
        "PROJECTION_BASED",
        description="Provenance: CONFIRMED_OBSERVATION, PROJECTION_BASED, DATA_DEFICIT_ADVISORY, SYNTHETIC_DEMO"
    )
    limitations: Any = Field(..., description="Assumptions, risks, and data prerequisites")
    created_at: datetime | None = None


class RecommendationListResponse(BaseModel):
    """API response model for listing policy recommendations."""

    total_recommendations: int
    expansion_count: int
    curriculum_pivot_count: int
    apprenticeship_count: int
    data_audit_count: int
    items: list[PolicyRecommendationItem]
