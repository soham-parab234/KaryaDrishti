"""Tests for Phase 12: Governance, Audit Logging, and Algorithmic Explainability."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.services.audit_service import (
    record_audit_event,
    query_audit_events,
    get_explainability_topic,
    list_all_explainability_topics,
)


def test_record_and_query_audit_service(db_session: Session):
    """Verify that audit events are recorded with UUIDs and queryable."""
    event = record_audit_event(
        db=db_session,
        event_type="TEST_EVENT",
        entity_type="TEST_ENTITY",
        entity_id="ENT-001",
        action_summary="Executed unit test audit entry",
        actor="PYTEST_RUNNER",
        details={"metric": 42, "status": "OK"},
    )
    assert event.id is not None
    assert event.event_id.startswith("AUD-")
    assert event.actor == "PYTEST_RUNNER"

    # Query filtered events
    logs = query_audit_events(db_session, event_type="TEST_EVENT")
    assert len(logs) >= 1
    assert any(l.event_id == event.event_id for l in logs)


def test_explainability_service_dossiers():
    """Verify explainability documentation content and mathematical rigor."""
    topics = list_all_explainability_topics()
    assert "forecast_intervals" in topics
    assert "gap_formulas" in topics
    assert "alert_triggers" in topics
    assert "recommendation_logic" in topics

    # Test forecast intervals mathematical disclosure
    fcst_doc = get_explainability_topic("forecast_intervals")
    assert fcst_doc is not None
    assert "sigma_h^2" in fcst_doc["mathematical_formula"]
    assert "80%" in fcst_doc["coverage_level"]
    assert len(fcst_doc["assumptions"]) >= 2
    assert len(fcst_doc["limitations"]) >= 1

    # Test gap formulas disclosure
    gap_doc = get_explainability_topic("gap_formulas")
    assert gap_doc is not None
    assert "Demand - Qualified Supply" in gap_doc["mathematical_formula"]
    assert any("Capacity vs. Supply" in r for r in gap_doc["data_compatibility_rules"])


def test_api_audit_logs_endpoint(client: TestClient):
    """Verify GET /api/governance/audit-logs returns JSON audit history."""
    response = client.get("/api/governance/audit-logs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_explainability_endpoints(client: TestClient):
    """Verify GET /api/governance/explainability topics and detail dossier."""
    # List topics
    list_resp = client.get("/api/governance/explainability")
    assert list_resp.status_code == 200
    topics_data = list_resp.json()
    assert "available_topics" in topics_data
    assert len(topics_data["available_topics"]) >= 4

    # Detail dossier
    detail_resp = client.get("/api/governance/explainability/forecast_intervals")
    assert detail_resp.status_code == 200
    doc = detail_resp.json()
    assert "mathematical_formula" in doc
    assert "assumptions" in doc

    # Unknown topic returns 404
    unknown_resp = client.get("/api/governance/explainability/non_existent_topic")
    assert unknown_resp.status_code == 404
    assert "Available topics" in unknown_resp.json()["detail"]


def test_pipeline_recompute_generates_audit_event(client: TestClient):
    """Verify that recomputing intelligence pipeline writes an audit log."""
    recompute_resp = client.post("/api/analytics/recompute-pipeline")
    assert recompute_resp.status_code == 200

    # Check audit log contains PIPELINE_RECOMPUTE event
    logs_resp = client.get("/api/governance/audit-logs?event_type=PIPELINE_RECOMPUTE")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) > 0
    latest = logs[0]
    assert latest["event_type"] == "PIPELINE_RECOMPUTE"
    assert latest["actor"] == "SYSTEM_PIPELINE"
    assert "approved_vacancies" in latest["details"]
