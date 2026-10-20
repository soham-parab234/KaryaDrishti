"""Pydantic schemas for training-seat scenario planning.

Conforms strictly to LMIS Master R&D Section 10:
- Scenario Entrants = Additional Seats × Enrolment Rate × Completion Rate × Local Entry Rate
- Validates parameter ranges, displays formula steps, and documents operational assumptions.
- Explicitly labels results as scenario estimates, NOT official policy allocations.
"""

from pydantic import BaseModel, Field


class ScenarioCalculationRequest(BaseModel):
    """Input parameters for calculating a training-seat expansion scenario."""

    nco_code: str = Field(..., description="NCO-2015 8-digit occupation code")
    district_code: str = Field(..., description="Target district identifier (e.g. 'MH_PUN')")
    reporting_period: str = Field(..., description="Target planning period (e.g. '2026-10')")
    baseline_gap: float = Field(..., description="Baseline estimated worker shortage (or negative for oversupply)")
    proposed_additional_seats: int = Field(
        ...,
        ge=0,
        le=50000,
        description="Proposed additional sanctioned training seats",
    )
    enrolment_rate_pct: float = Field(
        90.0,
        ge=0.0,
        le=100.0,
        description="Assumed proportion of offered seats that are actually taken up (%)",
    )
    completion_rate_pct: float = Field(
        85.0,
        ge=0.0,
        le=100.0,
        description="Assumed proportion of enrolled trainees who complete curriculum (%)",
    )
    local_entry_rate_pct: float = Field(
        70.0,
        ge=0.0,
        le=100.0,
        description="Assumed proportion of completers entering the target occupation and geography (%)",
    )
    estimated_cost_per_seat_inr: float = Field(
        18500.0,
        ge=0.0,
        description="Estimated operational expenditure per sanctioned training seat in INR",
    )
    trainee_trainer_ratio: int = Field(
        20,
        ge=1,
        le=50,
        description="Trainees per qualified instructor/trainer ratio",
    )


class ScenarioCalculationResponse(BaseModel):
    """Transparent calculation output with formula breakdown and policy caveats."""

    nco_code: str
    canonical_title: str | None = None
    district_code: str
    reporting_period: str
    baseline_gap: float
    proposed_additional_seats: int
    enrolment_rate_pct: float
    completion_rate_pct: float
    local_entry_rate_pct: float

    # Calculated metrics
    effective_yield_per_seat: float = Field(
        ...,
        description="Expected yield factor = (Enrolment / 100) * (Completion / 100) * (Local Entry / 100)",
    )
    scenario_entrants: float = Field(
        ...,
        description="Scenario Entrants = Additional Seats * Effective Yield Factor",
    )
    residual_gap: float = Field(
        ...,
        description="Residual Shortage = Baseline Gap - Scenario Entrants (lower is better for shortages)",
    )
    gap_reduction_pct: float = Field(
        ...,
        description="Percentage of baseline shortage addressed by scenario entrants",
    )

    # Operational requirements
    estimated_budget_inr: float = Field(..., description="Estimated total cost = Seats * Cost per seat")
    estimated_trainers_required: int = Field(..., description="Trainers needed = ceil(Seats / Trainee ratio)")

    # Formula transparency and governance
    formula_used: str = Field(
        "Scenario Entrants = Additional Seats × (Enrolment Rate / 100) × (Completion Rate / 100) × (Local Entry Rate / 100)",
        description="Exact Master R&D Section 10 conversion formula",
    )
    calculation_steps: list[str] = Field(default_factory=list)
    is_scenario_only: bool = Field(
        True,
        description="Notice: This is a scenario calculation, NOT a policy allocation automatically approved by government",
    )
    policy_disclaimer: str = Field(
        "Training seats represent institutional capacity, not immediate labour market entrants. "
        "Training cycles entail lag times (typically 3 to 12 months), and local retention depends on market wage rates.",
        description="Governance disclaimer",
    )
    limitations: list[str] = Field(default_factory=list)
