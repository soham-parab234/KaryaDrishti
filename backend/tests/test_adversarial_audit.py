"""Adversarial Regression Tests for LMIS Engine.

Specifically tests:
1. Cryptographic tamper-evidence: modifying or deleting an audit record is mathematically detected.
2. Discontinuous time series: gaps in monthly reporting periods generate explicit warnings.
3. Negative value sanitization: negative demand/supply inputs are clamped at zero and flagged.
4. Duplicate synthetic baseline deduplication: repeated baseline seeds do not double-count demand.
5. Alert triage persistence and audit logging: planning actions update DB and record audit events.
6. Verification endpoint /api/governance/audit-logs/verify works end-to-end.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.analytics import DemandObservation
from backend.app.models.alerts import EarlyWarningAlert
from backend.app.models.audit import AuditEvent
from backend.app.services.audit_service import (
    record_audit_event,
    verify_audit_log_integrity,
)
from backend.app.services.forecasting import (
    reconcile_time_series_observations,
    TimeSeriesObservation,
)



def test_audit_log_cryptographic_tamper_evidence_modification_detected(db_session: Session):
    """Test that modifying any payload or actor field in an audit record breaks the SHA-256 chain."""
    db_session.query(AuditEvent).delete()
    db_session.commit()

    # Create 3 valid audit events
    e1 = record_audit_event(db_session, "INGESTION_IMPORT", "BATCH", "B-001", "Import batch 1", actor="OFFICER_A")
    e2 = record_audit_event(db_session, "REVIEW_DECISION_APPROVED", "OCCUPATION", "OCC-001", "Approved title", actor="OFFICER_B")
    e3 = record_audit_event(db_session, "PIPELINE_RECOMPUTE", "PIPELINE", "ALL", "Recompute pipeline", actor="SYSTEM")

    # Verify pristine chain is valid
    report = verify_audit_log_integrity(db_session)
    assert report["is_valid"] is True
    assert report["total_events"] == 3

    # Adversarial attack: directly alter e2's action_summary in the database without updating hash
    e2.action_summary = "TAMPERED: Altered decision summary"
    db_session.commit()

    # Verify tampering is detected
    tamper_report = verify_audit_log_integrity(db_session)
    assert tamper_report["is_valid"] is False
    assert tamper_report["corrupted_event_id"] == e2.event_id
    assert "Record modification detected" in tamper_report["failure_reason"]


def test_audit_log_cryptographic_tamper_evidence_deletion_detected(db_session: Session):
    """Test that deleting an intermediate audit event breaks the chain link."""
    db_session.query(AuditEvent).delete()
    db_session.commit()

    # Create 3 valid audit events
    e1 = record_audit_event(db_session, "INGESTION_IMPORT", "BATCH", "B-101", "Import 101")
    e2 = record_audit_event(db_session, "INGESTION_IMPORT", "BATCH", "B-102", "Import 102")
    e3 = record_audit_event(db_session, "INGESTION_IMPORT", "BATCH", "B-103", "Import 103")

    report = verify_audit_log_integrity(db_session)
    assert report["is_valid"] is True
    assert report["total_events"] == 3

    # Adversarial attack: delete e2 from database
    deleted_id = e2.event_id
    db_session.delete(e2)
    db_session.commit()

    # Verify deletion is detected because e3.prev_hash no longer matches e1.record_hash
    del_report = verify_audit_log_integrity(db_session)
    assert del_report["is_valid"] is False
    assert del_report["corrupted_event_id"] == e3.event_id
    assert "Chain link broken" in del_report["failure_reason"]


def test_forecasting_discontinuous_time_series_detection():
    """Test that missing months in a time series are surfaced in limitations."""
    records = [
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period="2025-01",
            demand_value=100.0,
            source_system="BATCH",
            data_status="IMPORTED",
        ),
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period="2025-02",
            demand_value=110.0,
            source_system="BATCH",
            data_status="IMPORTED",
        ),
        # Missing 2025-03 and 2025-04 (2 missing months)
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period="2025-05",
            demand_value=120.0,
            source_system="BATCH",
            data_status="IMPORTED",
        ),
    ]

    reconciled, status, limitations = reconcile_time_series_observations(records, "DEMAND")
    assert len(reconciled) == 3
    assert any("DISCONTINUOUS TIME SERIES" in lim for lim in limitations)
    assert any("missing 2 calendar month(s)" in lim for lim in limitations)


def test_forecasting_negative_values_sanitization():
    """Test that negative observations are clamped to 0.0 and disclosed."""
    records = [
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period="2025-01",
            demand_value=-50.0,
            source_system="DIRTY_DATA",
            data_status="IMPORTED",
        )
    ]

    reconciled, status, limitations = reconcile_time_series_observations(records, "DEMAND")
    assert len(reconciled) == 1
    assert reconciled[0].value == 0.0
    assert any("DATA SANITIZATION" in lim for lim in limitations)


def test_forecasting_duplicate_synthetic_baseline_not_doubled():
    """Test that duplicate synthetic baseline records for the same month do not sum."""
    records = [
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period="2026-07",
            demand_value=680.0,
            source_system="SEED_RUN_1",
            data_status="SYNTHETIC_DEMO",
        ),
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period="2026-07",
            demand_value=680.0,
            source_system="SEED_RUN_2",
            data_status="SYNTHETIC_DEMO",
        ),
    ]

    reconciled, status, limitations = reconcile_time_series_observations(records, "DEMAND")
    assert len(reconciled) == 1
    # Must NOT be 1360.0
    assert reconciled[0].value == 680.0
    assert status == "SYNTHETIC_DEMO"


def test_alert_triage_api_and_audit_persistence(client: TestClient, db_session: Session):
    """Test PATCH /api/alerts/{alert_id}/triage persists and generates audit event."""
    alert = EarlyWarningAlert(
        alert_id="ALT-TEST-TRIAGE-001",
        nco_code="7421.0301",
        canonical_title="Solar PV Technician",
        district_code="MH_PUN",
        reporting_period="2026-07",
        alert_type="SHORTAGE_RISK",
        severity="CRITICAL",
        title="Critical Shortage Alert",
        trigger_rule="Gap rate >= 35%",
        evidence_summary="Demand=680, Supply=420",
        review_action_recommended="Sanction additional intake seats",
        observed_demand=680.0,
        estimated_supply=420.0,
        absolute_gap=260.0,
        gap_rate_pct=38.2,
        triage_status="NEW",
        threshold_type="PROTOTYPE_DEFAULT",
        data_status="SYNTHETIC_DEMO",
        limitations="Pilot baseline.",
    )
    db_session.add(alert)
    db_session.commit()

    # Send triage update
    response = client.patch(
        "/api/alerts/ALT-TEST-TRIAGE-001/triage",
        json={
            "triage_status": "ACKNOWLEDGED",
            "triage_note": "Reviewed by Director of Vocational Training",
            "actor": "DIRECTOR_VT",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["triage_status"] == "ACKNOWLEDGED"
    assert data["triage_note"] == "Reviewed by Director of Vocational Training"

    # Verify DB persistence
    refreshed = db_session.query(EarlyWarningAlert).filter(EarlyWarningAlert.alert_id == "ALT-TEST-TRIAGE-001").first()
    assert refreshed.triage_status == "ACKNOWLEDGED"

    # Verify Audit trail was written
    audit_evt = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.event_type == "ALERT_TRIAGE", AuditEvent.entity_id == "ALT-TEST-TRIAGE-001")
        .first()
    )
    assert audit_evt is not None
    assert audit_evt.actor == "DIRECTOR_VT"
    assert audit_evt.record_hash is not None


def test_api_governance_verify_endpoint(client: TestClient):
    """Test GET /api/governance/audit-logs/verify endpoint."""
    response = client.get("/api/governance/audit-logs/verify")
    assert response.status_code == 200
    data = response.json()
    assert "is_valid" in data
    assert "total_events" in data
    assert data["is_valid"] is True
