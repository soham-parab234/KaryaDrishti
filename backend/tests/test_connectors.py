"""Tests for Phase 11: Data Integration Readiness and Connectors."""

import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.services.connectors import (
    PostingsCsvAdapter,
    TrainingSupplyCsvAdapter,
    list_all_connectors,
)
from backend.app.services.connectors.planned_connectors import (
    NcsApiConnector,
    EShramApiConnector,
    NcvetSipConnector,
)
from backend.app.models.analytics import TrainingCapacityOutcome


def test_list_all_connectors_metadata():
    """Verify that all connectors are registered and have accurate statuses and disclaimers."""
    connectors = list_all_connectors()
    assert len(connectors) == 5

    ids = {c.connector_id for c in connectors}
    assert "POSTINGS_CSV_ADAPTER" in ids
    assert "TRAINING_SUPPLY_CSV_ADAPTER" in ids
    assert "NCS_API_CONNECTOR" in ids
    assert "ESHRAM_API_CONNECTOR" in ids
    assert "NCVET_SIP_CONNECTOR" in ids

    for c in connectors:
        if "PLANNED" in c.connection_status:
            assert c.is_live_connection is False
            assert "planned" in c.description.lower() or "requires" in c.limitations_notice.lower()
            assert len(c.verification_disclaimer) > 10


def test_training_supply_adapter_validation_and_import(db_session: Session):
    """Verify validation and import of institutional training capacity CSV."""
    adapter = TrainingSupplyCsvAdapter()

    valid_csv = (
        "nco_code,district_code,reporting_period,sanctioned_seats,enrolled_students,completed_students,placed_students,source_system\n"
        "7233.0100,MH_PUN,2026-03,120,110,95,70,DGT_MIS\n"
        "7421.0301,MH_NSK,2026-03,80,75,65,50,STATE_ITI_PORTAL\n"
    ).encode("utf-8")

    val_res = adapter.validate_input(valid_csv)
    assert val_res["is_valid"] is True
    assert val_res["total_rows"] == 2
    assert val_res["valid_rows"] == 2
    assert len(val_res["errors"]) == 0

    imp_res = adapter.import_data(valid_csv, db=db_session)
    assert imp_res["status"] == "COMPLETED"
    assert imp_res["records_persisted"] == 2

    # Check persistence in database
    rec1 = (
        db_session.query(TrainingCapacityOutcome)
        .filter(
            TrainingCapacityOutcome.nco_code == "7233.0100",
            TrainingCapacityOutcome.district_code == "MH_PUN",
            TrainingCapacityOutcome.source_system == "DGT_MIS",
        )
        .first()
    )
    assert rec1 is not None
    assert rec1.sanctioned_seats == 120
    assert rec1.enrolled_students == 110
    assert rec1.completed_students == 95
    assert rec1.placed_students == 70
    assert rec1.placement_rate_pct == round((70 / 95) * 100.0, 1)
    assert rec1.data_status == "IMPORTED"


def test_training_supply_adapter_catches_invalid_logical_constraints():
    """Verify that logical errors (completed > enrolled, placed > completed) are caught."""
    adapter = TrainingSupplyCsvAdapter()

    invalid_csv = (
        "nco_code,district_code,reporting_period,sanctioned_seats,enrolled_students,completed_students,placed_students,source_system\n"
        "7233.0100,MH_PUN,2026-03,100,50,80,90,STATE_MIS\n"  # completed (80) > enrolled (50), placed (90) > completed (80)
    ).encode("utf-8")

    val_res = adapter.validate_input(invalid_csv)
    assert val_res["is_valid"] is False
    assert val_res["rejected_rows"] >= 2
    error_types = {e["error_type"] for e in val_res["errors"]}
    assert "LOGICAL_CONSTRAINT" in error_types


def test_planned_government_connectors_fail_safely(db_session: Session):
    """Ensure planned government connectors fail safely without claiming live integration."""
    ncs = NcsApiConnector()
    eshram = EShramApiConnector()
    sidh = NcvetSipConnector()

    assert ncs.get_metadata().is_live_connection is False
    assert eshram.get_metadata().is_live_connection is False
    assert sidh.get_metadata().is_live_connection is False

    import pytest
    with pytest.raises(NotImplementedError):
        ncs.import_data(b"{}", db_session)
    with pytest.raises(NotImplementedError):
        eshram.import_data(b"{}", db_session)
    with pytest.raises(NotImplementedError):
        sidh.import_data(b"{}", db_session)


def test_api_connectors_and_supply_endpoints(client: TestClient):
    """Verify API endpoints for connectors, supply validation, and supply import."""
    # 1. GET /api/ingestion/connectors
    conn_res = client.get("/api/ingestion/connectors")
    assert conn_res.status_code == 200
    connectors = conn_res.json()
    assert len(connectors) == 5

    # 2. POST /api/ingestion/validate-supply
    valid_csv = (
        "nco_code,district_code,reporting_period,sanctioned_seats,enrolled_students,completed_students,placed_students,source_system\n"
        "7233.0100,MH_PUN,2026-03,60,55,50,40,DGT_MIS\n"
    )
    files = {"file": ("test_supply.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")}
    val_res = client.post("/api/ingestion/validate-supply", files=files)
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # 3. POST /api/ingestion/import-supply
    files2 = {"file": ("test_supply.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")}
    imp_res = client.post("/api/ingestion/import-supply", files=files2)
    assert imp_res.status_code == 201
    assert imp_res.json()["status"] == "COMPLETED"
    assert imp_res.json()["records_persisted"] == 1
