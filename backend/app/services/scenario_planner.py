"""Training-Seat Scenario Planning Engine.

Conforms strictly to LMIS Master R&D Section 10:
Formula:
  Scenario Entrants = Additional Seats × Enrolment Rate × Completion Rate × Local Entry Rate

- Validates rate boundaries [0.0, 100.0] and non-negative seat counts.
- Displays full calculation steps and operational constraints (budget, instructors).
- Prevents double counting and clearly distinguishes scenario estimates from verified facts.
"""

import math
from sqlalchemy.orm import Session
from backend.app.models.occupation import NcoOccupation
from backend.app.schemas.scenarios import (
    ScenarioCalculationRequest,
    ScenarioCalculationResponse,
)


def calculate_training_scenario(
    request: ScenarioCalculationRequest,
    db: Session | None = None,
) -> ScenarioCalculationResponse:
    """Execute transparent training-seat conversion scenario calculation."""
    # 1. Fetch title if DB provided
    canonical_title = None
    if db:
        occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == request.nco_code).first()
        if occ:
            canonical_title = occ.canonical_title

    seats = request.proposed_additional_seats
    enrol_frac = request.enrolment_rate_pct / 100.0
    comp_frac = request.completion_rate_pct / 100.0
    entry_frac = request.local_entry_rate_pct / 100.0

    # Effective yield factor per seat
    effective_yield = enrol_frac * comp_frac * entry_frac

    # Expected net entrants into target occupation & district
    expected_entrants = round(seats * effective_yield, 1)

    # Residual gap
    baseline = request.baseline_gap
    residual = round(baseline - expected_entrants, 1)

    # Gap reduction percentage
    if baseline > 0:
        gap_reduction_pct = round(min(100.0, max(0.0, (expected_entrants / baseline) * 100.0)), 1)
    else:
        gap_reduction_pct = 0.0

    # Operational calculations
    budget_inr = round(seats * request.estimated_cost_per_seat_inr, 2)
    ratio = max(1, request.trainee_trainer_ratio)
    trainers_needed = math.ceil(seats / ratio) if seats > 0 else 0

    # Build step-by-step audit trail
    enrolled_est = round(seats * enrol_frac, 1)
    completed_est = round(enrolled_est * comp_frac, 1)

    calculation_steps = [
        f"1. Sanctioned Intake: {seats} additional training seat(s) proposed.",
        f"2. Enrolment Take-Up: {seats} seats × {request.enrolment_rate_pct:.1f}% = {enrolled_est} trainee(s) enrolled.",
        f"3. Course Completion: {enrolled_est} trainees × {request.completion_rate_pct:.1f}% = {completed_est} completer(s).",
        f"4. Local Occupation Entry: {completed_est} completers × {request.local_entry_rate_pct:.1f}% = {expected_entrants} qualified entrant(s).",
        f"5. Shortage Impact: Baseline gap of {baseline} is reduced by {expected_entrants} to a residual gap of {residual} ({gap_reduction_pct}% gap closure).",
    ]

    limitations = [
        "Scenario calculation only: Does NOT represent an approved government budget or seat sanction.",
        "Capacity vs. Supply: Sanctioned seats require 3 to 12 months curriculum lead time before trainees enter the market.",
        "Wage & Retention: Model assumes graduates will enter the local market; competitive out-migration or below-market wages will lower actual retention.",
        f"Operational Feasibility: Implementation requires ~{trainers_needed} certified trainer(s) and an estimated capital/operating budget of ₹{budget_inr:,.0f}.",
    ]

    if seats == 0:
        limitations.append("Notice: Zero additional seats proposed; existing baseline equilibrium remains unchanged.")

    return ScenarioCalculationResponse(
        nco_code=request.nco_code,
        canonical_title=canonical_title,
        district_code=request.district_code,
        reporting_period=request.reporting_period,
        baseline_gap=baseline,
        proposed_additional_seats=seats,
        enrolment_rate_pct=request.enrolment_rate_pct,
        completion_rate_pct=request.completion_rate_pct,
        local_entry_rate_pct=request.local_entry_rate_pct,
        effective_yield_per_seat=round(effective_yield, 4),
        scenario_entrants=expected_entrants,
        residual_gap=residual,
        gap_reduction_pct=gap_reduction_pct,
        estimated_budget_inr=budget_inr,
        estimated_trainers_required=trainers_needed,
        formula_used=(
            "Scenario Entrants = Additional Seats × (Enrolment Rate / 100) × "
            "(Completion Rate / 100) × (Local Entry Rate / 100)"
        ),
        calculation_steps=calculation_steps,
        is_scenario_only=True,
        policy_disclaimer=(
            "Training seats represent institutional capacity, not immediate labour market entrants. "
            "Policy decisions require joint review of accredited infrastructure, faculty availability, and employer wage levels."
        ),
        limitations=limitations,
    )
