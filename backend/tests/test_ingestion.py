"""Automated tests for CSV ingestion, validation, persistence, and error handling."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.ingestion import ImportBatch, IngestedPostingRecord

VALID_CSV_CONTENT = """posting_id,raw_title,district_code,observation_date,source_system,vacancy_count
PST-2026-001,Solar PV Rooftop Technician,MH_PUN,2026-10-10,NCS_FEED,2
PST-2026-002,CNC Turning Machine Operator,MH_NSK,2026-10-11,PORTAL_SCRAPE,1
PST-2026-003,Embedded Firmware Engineer,MH_PUN,2026-10-12,SCHEME_MIS,5
"""

def test_validate_valid_csv(client: TestClient):
    """POST /api/ingestion/validate should succeed with status 'VALID' for clean data."""
    files = {"file": ("test_valid.csv", VALID_CSV_CONTENT.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALID"
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3
    assert data["rejected_rows"] == 0
    assert len(data["errors"]) == 0
    assert len(data["sample_valid_records"]) == 3

def test_validate_missing_required_columns(client: TestClient):
    """POST /api/ingestion/validate should flag missing required schema columns."""
    bad_csv = """posting_id,raw_title,observation_date
PST-2026-001,Solar PV Tech,2026-10-10
"""
    files = {"file": ("bad_headers.csv", bad_csv.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ERROR"
    assert any("district_code" in err["error_message"] for err in data["errors"])

def test_validate_duplicate_headers(client: TestClient):
    """POST /api/ingestion/validate should detect and report duplicate column headers."""
    dup_header_csv = """posting_id,raw_title,posting_id,district_code,observation_date,source_system
PST-2026-001,Solar Tech,DUP,MH_PUN,2026-10-10,NCS_FEED
"""
    files = {"file": ("dup_headers.csv", dup_header_csv.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ERROR"
    assert any("Duplicate column header" in err["error_message"] for err in data["errors"])

def test_validate_empty_csv_file(client: TestClient):
    """POST /api/ingestion/validate should reject a 0-byte file gracefully."""
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ERROR"
    assert any("completely empty" in err["error_message"] for err in data["errors"])

def test_validate_header_only_csv(client: TestClient):
    """POST /api/ingestion/validate should detect when header exists but no data rows."""
    header_only = "posting_id,raw_title,district_code,observation_date,source_system,vacancy_count\n"
    files = {"file": ("header_only.csv", header_only.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INVALID"
    assert data["total_rows"] == 0
    assert any("zero data records" in err["error_message"] for err in data["errors"])

def test_validate_invalid_row_values(client: TestClient):
    """POST /api/ingestion/validate should capture row-level field violations with row numbers."""
    invalid_rows_csv = """posting_id,raw_title,district_code,observation_date,source_system,vacancy_count
PST-2026-010,,MH_PUN,2026-10-10,NCS_FEED,1
PST-2026-011,Valid Job Title,XX_UNKNOWN,2026-10-10,NCS_FEED,1
PST-2026-012,Future Observation,MH_PUN,2099-01-01,NCS_FEED,1
PST-2026-013,Invalid Source Feed,MH_NSK,2026-10-10,UNOFFICIAL_BLOG,1
PST-2026-014,Negative Vacancy Count,MH_PUN,2026-10-10,NCS_FEED,-3
"""
    files = {"file": ("invalid_rows.csv", invalid_rows_csv.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INVALID"
    assert data["total_rows"] == 5
    assert data["valid_rows"] == 0
    assert data["rejected_rows"] == 5

    # Verify specific row numbers and error fields
    row_error_fields = {(err["row_number"], err["field"]) for err in data["errors"]}
    assert (2, "raw_title") in row_error_fields
    assert (3, "district_code") in row_error_fields
    assert (4, "observation_date") in row_error_fields
    assert (5, "source_system") in row_error_fields
    assert (6, "vacancy_count") in row_error_fields

def test_validate_malformed_csv_columns(client: TestClient):
    """POST /api/ingestion/validate should detect rows with missing or extra columns."""
    malformed_csv = """posting_id,raw_title,district_code,observation_date,source_system
PST-1,OnlyTwoColumns
PST-2,Too,Many,Columns,Here,Extra,Field
"""
    files = {"file": ("malformed.csv", malformed_csv.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INVALID"
    assert any("Malformed row" in err["error_message"] for err in data["errors"])

def test_validate_utf8_bom_encoding(client: TestClient):
    """POST /api/ingestion/validate should handle UTF-8 files exported with BOM."""
    bom_bytes = b"\xef\xbb\xbf" + VALID_CSV_CONTENT.encode("utf-8")
    files = {"file": ("with_bom.csv", bom_bytes, "text/csv")}
    response = client.post("/api/ingestion/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALID"
    assert data["valid_rows"] == 3

def test_import_valid_csv_persists_to_db(client: TestClient, db_session: Session):
    """POST /api/ingestion/import should persist validated batch metadata and records."""
    files = {"file": ("valid_import.csv", VALID_CSV_CONTENT.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/import", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["total_rows"] == 3
    assert data["imported_rows"] == 3
    assert "BATCH-" in data["batch_id"]

    batch_id = data["batch_id"]

    # Verify database persistence
    batch = db_session.query(ImportBatch).filter(ImportBatch.batch_id == batch_id).first()
    assert batch is not None
    assert batch.filename == "valid_import.csv"
    assert batch.total_rows == 3

    records = db_session.query(IngestedPostingRecord).filter(IngestedPostingRecord.batch_id == batch_id).all()
    assert len(records) == 3
    assert any(r.posting_id == "PST-2026-001" and r.district_code == "MH_PUN" for r in records)

    # Verify audit ledger endpoint
    ledger_res = client.get("/api/ingestion/batches")
    assert ledger_res.status_code == 200
    ledger_data = ledger_res.json()
    assert len(ledger_data) >= 1
    assert any(b["batch_id"] == batch_id for b in ledger_data)

def test_duplicate_import_handling(client: TestClient):
    """POST /api/ingestion/import should reject duplicate submissions of the identical CSV."""
    unique_content = f"""posting_id,raw_title,district_code,observation_date,source_system
PST-DUP-01,Unique Batch Job 1,MH_PUN,2026-10-10,NCS_FEED
"""
    files = {"file": ("unique_batch.csv", unique_content.encode("utf-8"), "text/csv")}

    # First import: should succeed
    res1 = client.post("/api/ingestion/import", files=files)
    assert res1.status_code == 201

    # Second import with identical file content: should be rejected as duplicate
    files_again = {"file": ("unique_batch_copy.csv", unique_content.encode("utf-8"), "text/csv")}
    res2 = client.post("/api/ingestion/import", files=files_again)
    assert res2.status_code == 409
    assert "Duplicate batch detected" in res2.json()["detail"]

def test_import_rejects_invalid_csv_atomic(client: TestClient, db_session: Session):
    """POST /api/ingestion/import must reject batches with invalid records without saving partial rows."""
    mixed_content = """posting_id,raw_title,district_code,observation_date,source_system
PST-GOOD-1,Good Job Title,MH_PUN,2026-10-10,NCS_FEED
PST-BAD-2,,MH_PUN,2026-10-10,NCS_FEED
"""
    files = {"file": ("mixed.csv", mixed_content.encode("utf-8"), "text/csv")}
    response = client.post("/api/ingestion/import", files=files)
    assert response.status_code == 422
    data = response.json()
    assert "Batch validation failed" in data["detail"]["error"]

    # Verify zero records from this mixed file were inserted into the DB
    bad_record = db_session.query(IngestedPostingRecord).filter(IngestedPostingRecord.posting_id == "PST-GOOD-1").first()
    assert bad_record is None
