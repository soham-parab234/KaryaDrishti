"""Pydantic schemas for early-warning alerts.

Conforms to LMIS Master R&D Section 11:
- Four alert categories: SHORTAGE_RISK, OVERSUPPLY_RISK, EMERGING_DEMAND, DATA_QUALITY_WARNING.
- Explicit severity, trigger rules, supporting numerical metrics, and action to review.
- Discloses prototype configurable default threshold status.
"""

from pydantic import BaseModel, Field


class EarlyWarningAlertItem(BaseModel):
    """Schema for individual early warning alert."""

    alert_id: str
    nco_code: str
    canonical_title: str | None = None
    district_code: str
    reporting_period: str
    alert_type: str = Field(
        ...,
        description="'SHORTAGE_RISK', 'OVERSUPPLY_RISK', 'PROJECTED_SHORTAGE_RISK', 'PROJECTED_OVERSUPPLY_RISK', 'EMERGING_DEMAND', or 'DATA_QUALITY_WARNING'",
    )
    severity: str = Field(..., description="'CRITICAL', 'WARNING', or 'INFO'")
    title: str
    trigger_rule: str
    evidence_summary: str
    review_action_recommended: str
    observed_demand: float | None = None
    estimated_supply: float | None = None
    absolute_gap: float | None = None
    gap_rate_pct: float | None = None
    threshold_type: str = Field(
        "CONFIGURABLE_PROTOTYPE_DEFAULT",
        description="Explicit notice that thresholds are prototype defaults, not official policy rules",
    )
    triage_status: str = Field("NEW", description="'NEW', 'ACKNOWLEDGED', 'ESCALATED', or 'RESOLVED'")
    triage_note: str | None = None
    data_status: str
    limitations: str
    created_at: str


class AlertTriageRequest(BaseModel):
    """Payload to update an alert's planning triage status."""

    triage_status: str = Field(..., description="'ACKNOWLEDGED', 'ESCALATED', or 'RESOLVED'")
    triage_note: str | None = Field(None, description="Optional planning officer justification note")
    actor: str = Field("PLANNING_OFFICER", description="Official or role applying the triage action")


class AlertEvaluationResponse(BaseModel):
    """Response returned when alerts evaluation engine runs."""

    total_alerts_evaluated: int
    critical_count: int
    warning_count: int
    info_count: int
    alerts: list[EarlyWarningAlertItem]
    message: str
