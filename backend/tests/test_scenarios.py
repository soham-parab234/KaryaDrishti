"""Tests for Phase 5B: Training-Seat Scenario Planner.

Verifies:
- Exact conversion formula: Scenario Entrants = Seats × Enrolment Rate × Completion Rate × Local Entry Rate
- Boundary values: 0 seats, 0% rate, 100% rate.
- Validation rejections: negative seats, rate > 100%.
- Step-by-step audit calculations and operational estimates (trainers, budget).
- Explicit policy disclaimers and limitations disclosure.
- GET /api/scenarios/defaults and POST /api/scenarios/calculate endpoints.
"""

from fastapi.testclient import TestClient


def test_scenario_calculation_master_rnd_example(client: TestClient):
    """Verify Master R&D Section 10 illustrative arithmetic:
    If shortage = 200, completion = 85%, local entry = 70% (with enrolment = 100%):
    Yield = 1.0 * 0.85 * 0.70 = 0.595.
    For ~336 seats, entrants = 336 * 0.595 = 199.9 ~ 200 workers.
    """
    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "baseline_gap": 200.0,
        "proposed_additional_seats": 336,
        "enrolment_rate_pct": 100.0,
        "completion_rate_pct": 85.0,
        "local_entry_rate_pct": 70.0,
        "estimated_cost_per_seat_inr": 18500.0,
        "trainee_trainer_ratio": 20,
    }
    res = client.post("/api/scenarios/calculate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["effective_yield_per_seat"] == 0.595
    # 336 * 0.595 = 199.92 -> rounded to 199.9
    assert abs(data["scenario_entrants"] - 199.9) < 0.2
    # Residual gap = 200 - 199.9 = 0.1
    assert abs(data["residual_gap"] - 0.1) < 0.2
    assert data["gap_reduction_pct"] >= 99.0
    # Budget: 336 * 18,500 = 6,216,000 INR
    assert data["estimated_budget_inr"] == 6216000.0
    # Trainers: ceil(336 / 20) = 17
    assert data["estimated_trainers_required"] == 17
    # Policy caveats
    assert data["is_scenario_only"] is True
    assert "Training seats represent institutional capacity" in data["policy_disclaimer"]
    assert len(data["calculation_steps"]) == 5


def test_scenario_zero_seats_produces_zero_entrants(client: TestClient):
    """Zero additional seats must yield zero entrants and leave baseline unchanged."""
    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "baseline_gap": 260.0,
        "proposed_additional_seats": 0,
        "enrolment_rate_pct": 90.0,
        "completion_rate_pct": 85.0,
        "local_entry_rate_pct": 70.0,
    }
    res = client.post("/api/scenarios/calculate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["scenario_entrants"] == 0.0
    assert data["residual_gap"] == 260.0
    assert data["gap_reduction_pct"] == 0.0
    assert data["estimated_trainers_required"] == 0
    assert data["estimated_budget_inr"] == 0.0
    assert any("Zero additional seats proposed" in lim for lim in data["limitations"])


def test_scenario_boundary_zero_rates(client: TestClient):
    """If completion rate or local entry rate is 0%, expected entrants must be 0."""
    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "baseline_gap": 150.0,
        "proposed_additional_seats": 500,
        "enrolment_rate_pct": 90.0,
        "completion_rate_pct": 0.0,  # Zero completion
        "local_entry_rate_pct": 70.0,
    }
    res = client.post("/api/scenarios/calculate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["effective_yield_per_seat"] == 0.0
    assert data["scenario_entrants"] == 0.0
    assert data["residual_gap"] == 150.0


def test_scenario_validation_rejects_negative_seats(client: TestClient):
    """Negative seat count must be rejected with 422 Unprocessable Entity."""
    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "baseline_gap": 100.0,
        "proposed_additional_seats": -50,
    }
    res = client.post("/api/scenarios/calculate", json=payload)
    assert res.status_code == 422


def test_scenario_validation_rejects_rates_above_100(client: TestClient):
    """Rate percentage exceeding 100% must be rejected with 422."""
    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "baseline_gap": 100.0,
        "proposed_additional_seats": 200,
        "enrolment_rate_pct": 125.0,  # Invalid rate > 100
    }
    res = client.post("/api/scenarios/calculate", json=payload)
    assert res.status_code == 422


def test_scenario_defaults_endpoint(client: TestClient):
    """GET /api/scenarios/defaults returns documented parameters and governance disclaimer."""
    res = client.get("/api/scenarios/defaults")
    assert res.status_code == 200
    data = res.json()
    assert "Additional Seats" in data["formula"]
    assert data["default_enrolment_rate_pct"] == 90.0
    assert data["default_completion_rate_pct"] == 85.0
    assert data["default_local_entry_rate_pct"] == 70.0
    assert "planner exploration" in data["governance_rule"]
