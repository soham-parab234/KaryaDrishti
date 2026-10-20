"""Tests for Phase 5A: Early-Warning Alerts Engine.

Verifies:
- Transparent rule-based alert triggering for Shortage Risk, Oversupply Risk, Emerging Demand, and Data Quality Warning.
- Severity classification (CRITICAL vs WARNING vs INFO).
- Insufficient evidence produces a DATA_QUALITY_WARNING rather than a fabricated high-risk shortage alert.
- Thresholds are explicitly disclosed as configurable prototype defaults.
- Endpoints GET /api/alerts and POST /api/alerts/evaluate work correctly.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.analytics import DemandObservation, QualifiedSupplyEstimate
from backend.app.services.alerts_service import evaluate_and_generate_alerts


def test_evaluate_and_list_alerts_endpoint(client: TestClient, db_session: Session):
    """GET /api/alerts should return seeded alerts ranked by severity."""
    res = client.get("/api/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) >= 1

    # Check Solar PV in Pune (Demand=680, Supply=420 -> Gap=+260, Gap Rate=38.2%)
    # This should trigger CRITICAL SHORTAGE_RISK because Gap Rate >= 35.0% and Absolute Gap >= 250
    solar_alert = next(
        (a for a in alerts if a["nco_code"] == "7421.0301" and a["district_code"] == "MH_PUN" and a["alert_type"] == "SHORTAGE_RISK"),
        None,
    )
    assert solar_alert is not None
    assert solar_alert["severity"] == "CRITICAL"
    assert solar_alert["absolute_gap"] == 260.0
    assert solar_alert["gap_rate_pct"] == 38.2
    assert "Prototype default rule" in solar_alert["trigger_rule"]
    assert solar_alert["threshold_type"] == "CONFIGURABLE_PROTOTYPE_DEFAULT"
    assert "additional accredited training seats" in solar_alert["review_action_recommended"]


def test_oversupply_risk_alert_detection(client: TestClient, db_session: Session):
    """IT Operations (NCO 3511.0101) in Pune has Demand=1250, Supply=1480 -> Gap=-230 (Oversupply)."""
    res = client.get("/api/alerts?alert_type=OVERSUPPLY_RISK")
    assert res.status_code == 200
    alerts = res.json()
    it_alert = next((a for a in alerts if a["nco_code"] == "3511.0101"), None)
    assert it_alert is not None
    assert it_alert["severity"] == "WARNING"
    assert it_alert["absolute_gap"] == -230.0
    assert "curriculum transition" in it_alert["review_action_recommended"]


def test_incomplete_evidence_triggers_data_warning_not_shortage(client: TestClient, db_session: Session):
    """When supply evidence is completely missing, the system must trigger DATA_QUALITY_WARNING, not a shortage."""
    # Add a demand record with no matching supply
    db_session.add(
        DemandObservation(
            nco_code="8888.0001",
            district_code="MH_DATA_GAP_DIST",
            reporting_period="2026-10",
            demand_value=500,
            unit="OBSERVED_POSTINGS",
            source_system="SYNTHETIC_TEST",
            observation_method="SYNTHETIC_DEMO",
            data_status="SYNTHETIC_DEMO",
            limitations="Single unverified demand point",
        )
    )
    db_session.commit()

    # Re-evaluate
    eval_res = client.post("/api/alerts/evaluate")
    assert eval_res.status_code == 200

    # Query alerts for this district
    res = client.get("/api/alerts?district_code=MH_DATA_GAP_DIST")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["alert_type"] == "DATA_QUALITY_WARNING"
    assert alert["severity"] == "WARNING"
    assert "MISSING_SUPPLY" in alert["trigger_rule"]
    # Absolute gap and gap rate must NOT be fabricated as a shortage
    assert alert["absolute_gap"] is None
    assert alert["gap_rate_pct"] is None
    assert "Avoid policy decisions" in alert["review_action_recommended"]


def test_filter_alerts_by_severity(client: TestClient):
    """GET /api/alerts?severity=CRITICAL should filter alerts cleanly."""
    res = client.get("/api/alerts?severity=CRITICAL")
    assert res.status_code == 200
    alerts = res.json()
    for a in alerts:
        assert a["severity"] == "CRITICAL"
