"""Training-Seat Scenario Planning API routes.

Conforms to LMIS Master R&D Section 10:
- POST /api/scenarios/calculate: Calculate scenario yield, residual shortage, budget, and faculty requirements.
- GET /api/scenarios/defaults: Get prototype baseline parameters and formula definitions.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.scenarios import (
    ScenarioCalculationRequest,
    ScenarioCalculationResponse,
)
from backend.app.services.scenario_planner import calculate_training_scenario

router = APIRouter(prefix="/scenarios", tags=["Scenario Planner"])


@router.post(
    "/calculate",
    response_model=ScenarioCalculationResponse,
    summary="Calculate training-seat scenario outcomes using Master R&D conversion formula",
)
def calculate_scenario(
    request: ScenarioCalculationRequest,
    db: Session = Depends(get_db),
):
    """Compute expected qualified entrants, residual gap, operational budget, and trainers required."""
    res = calculate_training_scenario(request, db=db)
    from backend.app.services.audit_service import record_audit_event
    record_audit_event(
        db=db,
        event_type="SCENARIO_SIMULATION",
        entity_type="SCENARIO",
        entity_id=f"{request.nco_code}-{request.district_code}",
        action_summary=f"Scenario evaluated for {request.nco_code} ({request.district_code}): +{request.proposed_additional_seats} seats",
        details={
            "nco_code": request.nco_code,
            "district_code": request.district_code,
            "proposed_seats": request.proposed_additional_seats,
            "expected_entrants": res.scenario_entrants,
            "residual_gap": res.residual_gap,
            "estimated_budget_inr": res.estimated_budget_inr,
        },
    )
    return res


@router.get(
    "/defaults",
    summary="Get documented prototype scenario conversion parameters and explanations",
)
def get_scenario_defaults():
    """Retrieve default conversion rates, operational costs, and formula specifications."""
    return {
        "formula": "Scenario Entrants = Additional Seats × Enrolment Rate × Completion Rate × Local Entry Rate",
        "default_enrolment_rate_pct": 90.0,
        "default_completion_rate_pct": 85.0,
        "default_local_entry_rate_pct": 70.0,
        "default_estimated_cost_per_seat_inr": 18500.0,
        "default_trainee_trainer_ratio": 20,
        "parameter_explanations": {
            "enrolment_rate": "Percentage of sanctioned seats that are physically occupied by admitted trainees.",
            "completion_rate": "Percentage of enrolled trainees who complete curriculum and obtain accredited certification.",
            "local_entry_rate": "Percentage of certified completers who enter and remain in the target occupation within the local district.",
            "effective_yield": "Product of the three conversion rates (e.g., 0.90 × 0.85 × 0.70 = 53.55% yield per seat).",
        },
        "governance_rule": (
            "Scenario calculations are intended for planner exploration and target-setting discussions. "
            "They do not constitute automated seat sanctions or official government budgetary approvals."
        ),
    }
