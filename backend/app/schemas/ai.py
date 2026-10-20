"""Pydantic schemas for the AI Labour Market Intelligence Assistant.

Conforms strictly to LMIS Master R&D and AI Handoff specifications:
- Grounded in SQLite analytical models.
- Read-only queries with explicit citations.
- Clearly distinguishes empirical vs. synthetic data provenance.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class AiEvidenceItem(BaseModel):
    """Specific quantitative record retrieved from the LMIS database to ground responses."""

    nco_code: str = Field(..., description="NCO-2015 8-digit occupation code")
    canonical_title: str = Field(..., description="Standardized occupation title")
    district_code: str = Field(..., description="Census district code (e.g. MH_PUN, MH_NSK)")
    reporting_period: str = Field(..., description="Reporting cycle snapshot (e.g. 2026-10)")
    demand_value: Optional[float] = Field(None, description="Observed/confirmed employer postings count")
    supply_value: Optional[float] = Field(None, description="Estimated qualified workforce pool")
    absolute_gap: Optional[float] = Field(None, description="Demand minus supply (positive = shortage)")
    gap_rate_pct: Optional[float] = Field(None, description="Gap rate percentage relative to demand")
    training_seats: Optional[int] = Field(None, description="Sanctioned institutional training seats (capacity)")
    placement_rate_pct: Optional[float] = Field(None, description="Vocational graduate placement rate")
    risk_level: Optional[str] = Field(None, description="Classification (e.g. CRITICAL_SHORTAGE, BALANCED)")
    data_status: str = Field("SYNTHETIC DEMO", description="Data provenance (SYNTHETIC DEMO, IMPORTED, REAL)")


class AiQueryRequest(BaseModel):
    """Payload submitted by user or planning officer."""

    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Natural language labour market intelligence query",
        examples=["Which occupations have the highest shortage in Pune?", "What is the forecast for Solar PV Technicians?"],
    )
    district_code: Optional[str] = Field(
        None,
        description="Optional district filter (e.g. 'MH_PUN', 'MH_NSK')",
    )
    occupation_code: Optional[str] = Field(
        None,
        description="Optional target NCO occupation code",
    )
    sector: Optional[str] = Field(
        None,
        description="Optional industry sector filter",
    )


class AiQueryResponse(BaseModel):
    """Standardized advisory response grounded in LMIS records."""

    query: str
    answer: str = Field(..., description="Executive advisory response")
    mode: str = Field(
        ...,
        description="'PROVIDER_LLM' if synthesized by external AI, or 'RULE_BASED_FALLBACK' if generated deterministically",
    )
    provider: str = Field(..., description="Active AI provider description or fallback engine indicator")
    status: str = Field("SUCCESS", description="Operation status ('SUCCESS', 'DEGRADED_FALLBACK', 'INSUFFICIENT_DATA')")
    evidence: list[AiEvidenceItem] = Field(default_factory=list, description="Retrieved database records used for grounding")
    limitations: list[str] = Field(default_factory=list, description="Methodological and data caveats")
    sources_used: list[str] = Field(default_factory=list, description="Specific database tables queried")
    disclaimer: str = Field(
        "Advisory decision support only. Grounded in Maharashtra Pilot Baseline. "
        "Does not modify official databases or constitute binding administrative sanction.",
        description="Legal and analytical disclaimer",
    )
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of response generation")
