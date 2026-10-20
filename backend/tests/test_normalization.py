"""Automated tests for NCO reference taxonomy, deterministic normalization, and review queue."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.occupation import NcoOccupation, OccupationAlias, TitleMappingReview

VALID_CSV_BATCH = """posting_id,raw_title,district_code,observation_date,source_system,vacancy_count
PST-NORM-001,Solar PV Installer,MH_PUN,2026-10-10,NCS_FEED,2
PST-NORM-002,CNC Mechanical Plant Service Fitter,MH_NSK,2026-10-11,PORTAL_SCRAPE,1
PST-NORM-003,Deep Sea Marine Diver Specialist,MH_PUN,2026-10-12,SCHEME_MIS,1
"""

def test_reference_taxonomy_seeded_and_queryable(client: TestClient):
    """GET /api/occupations/reference should return seeded pilot baseline occupations."""
    response = client.get("/api/occupations/reference")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    codes = [item["nco_code"] for item in data["items"]]
    assert "7421.0301" in codes
    assert "7233.0100" in codes
    assert "3511.0101" in codes

    # Test single code lookup
    single_res = client.get("/api/occupations/reference/7421.0301")
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["canonical_title"] == "Solar PV Installation & Maintenance Technician"
    assert single_data["division_code"] == "7"
    assert "Solar Rooftop Technician" in single_data["aliases"]

def test_reference_taxonomy_404_for_unknown_code(client: TestClient):
    """GET /api/occupations/reference/{nco_code} should return 404 for missing code."""
    response = client.get("/api/occupations/reference/9999.9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_normalize_exact_canonical_match(client: TestClient):
    """POST /api/normalization/normalize should return 100% confidence for exact canonical title."""
    payload = {"raw_title": "Solar PV Installation & Maintenance Technician"}
    response = client.post("/api/normalization/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROPOSED"
    assert data["match_method"] == "EXACT_CANONICAL"
    assert data["confidence"] == 100.0
    assert data["proposed_nco_code"] == "7421.0301"
    assert "Exact match" in data["match_rationale"]

def test_normalize_exact_verified_alias_match(client: TestClient):
    """POST /api/normalization/normalize should identify exact verified aliases with high confidence."""
    payload = {"raw_title": "Solar PV Installer"}
    response = client.post("/api/normalization/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROPOSED"
    assert data["match_method"] == "EXACT_ALIAS"
    assert data["confidence"] == 98.0
    assert data["proposed_nco_code"] == "7421.0301"

def test_normalize_abbreviation_expansion(client: TestClient):
    """POST /api/normalization/normalize should expand abbreviations like 'tech' and 'mech'."""
    payload = {"raw_title": "Solar Rooftop Tech"}
    response = client.post("/api/normalization/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["normalized_title"] == "solar rooftop technician"
    assert data["status"] == "PROPOSED"
    assert data["proposed_nco_code"] == "7421.0301"

def test_normalize_token_overlap_candidate_suggestion(client: TestClient):
    """POST /api/normalization/normalize should provide candidate matches for overlapping titles."""
    payload = {"raw_title": "CNC Mechanical Plant Service Fitter"}
    response = client.post("/api/normalization/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROPOSED"
    assert data["match_method"] in ("EXACT_ALIAS", "TOKEN_OVERLAP")
    assert data["proposed_nco_code"] == "7233.0100"
    assert data["confidence"] >= 70.0

def test_normalize_unmatched_unsupported_title(client: TestClient):
    """POST /api/normalization/normalize should mark titles with no reference support as UNMATCHED."""
    payload = {"raw_title": "Pediatric Neurosurgeon Specialist"}
    response = client.post("/api/normalization/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UNMATCHED"
    assert data["match_method"] == "NONE"
    assert data["confidence"] == 0.0
    assert data["proposed_nco_code"] is None
    assert "No exact match or supported candidate" in data["match_rationale"]

def test_batch_normalization_integration(client: TestClient, db_session: Session):
    """POST /api/normalization/process-batch/{batch_id} should connect ingested postings to reviews."""
    # 1. Ingest batch
    files = {"file": ("batch_norm.csv", VALID_CSV_BATCH.encode("utf-8"), "text/csv")}
    ingest_res = client.post("/api/ingestion/import", files=files)
    assert ingest_res.status_code == 201
    batch_id = ingest_res.json()["batch_id"]

    # 2. Run batch normalization
    proc_res = client.post(f"/api/normalization/process-batch/{batch_id}")
    assert proc_res.status_code == 200
    proc_data = proc_res.json()
    assert proc_data["total_postings_processed"] == 3
    assert proc_data["proposals_created"] == 3
    assert proc_data["proposed_count"] >= 2
    assert proc_data["unmatched_count"] >= 1  # Deep Sea Marine Diver is unmatched

    # 3. Query proposals endpoint
    prop_res = client.get(f"/api/normalization/proposals?batch_id={batch_id}")
    assert prop_res.status_code == 200
    proposals = prop_res.json()
    assert len(proposals) == 3

def test_human_review_approval_flow(client: TestClient, db_session: Session):
    """POST /api/normalization/proposals/{id}/review should approve mapping and learn alias."""
    # Create proposal in DB
    review = TitleMappingReview(
        raw_title="Solar PV Rooftop Lead Installer",
        normalized_title="solar pv rooftop lead installer",
        source_system="NCS_FEED",
        proposed_nco_code="7421.0301",
        proposed_canonical_title="Solar PV Installation & Maintenance Technician",
        match_method="TOKEN_OVERLAP",
        confidence=80.0,
        match_rationale="Token overlap with Solar PV Installer",
        status="PROPOSED",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    proposal_id = review.id

    # Review approval
    payload = {
        "decision": "APPROVED",
        "reviewer_note": "Verified by labour economist: meets Level 4 solar rooftop qualification pack.",
    }
    res = client.post(f"/api/normalization/proposals/{proposal_id}/review", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["assigned_nco_code"] == "7421.0301"

    # Verify DB persistence
    updated = db_session.query(TitleMappingReview).filter(TitleMappingReview.id == proposal_id).first()
    assert updated.status == "APPROVED"
    assert updated.reviewer_decision == "APPROVED"
    assert updated.reviewed_at is not None

    # Verify alias learned
    learned_alias = (
        db_session.query(OccupationAlias)
        .filter(
            OccupationAlias.nco_code == "7421.0301",
            OccupationAlias.alias_raw == "Solar PV Rooftop Lead Installer",
        )
        .first()
    )
    assert learned_alias is not None
    assert learned_alias.source == "REVIEWER_APPROVED"

def test_human_review_rejection_flow(client: TestClient, db_session: Session):
    """POST /api/normalization/proposals/{id}/review should allow rejecting an uncertain mapping."""
    review = TitleMappingReview(
        raw_title="Generic Factory Hand Helper",
        normalized_title="generic factory hand helper",
        source_system="PORTAL_SCRAPE",
        proposed_nco_code="7233.0100",
        proposed_canonical_title="Industrial Machinery Maintenance Mechanic",
        match_method="TOKEN_OVERLAP",
        confidence=45.0,
        match_rationale="Weak token overlap",
        status="PROPOSED",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    proposal_id = review.id

    payload = {
        "decision": "REJECTED",
        "reviewer_note": "General helper role does not possess specialized industrial maintenance skills.",
    }
    res = client.post(f"/api/normalization/proposals/{proposal_id}/review", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REJECTED"
    assert data["reviewer_decision"] == "REJECTED"

def test_human_review_invalid_nco_code_rejected(client: TestClient, db_session: Session):
    """POST /api/normalization/proposals/{id}/review should reject non-existent NCO codes."""
    review = TitleMappingReview(
        raw_title="Unassigned Title",
        normalized_title="unassigned title",
        source_system="SCHEME_MIS",
        status="UNMATCHED",
        match_method="NONE",
        confidence=0.0,
        match_rationale="No match",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    # Attempt to approve with fabricated NCO code
    payload = {
        "decision": "APPROVED",
        "override_nco_code": "9999.0000",
        "reviewer_note": "Attempted invalid code assignment",
    }
    res = client.post(f"/api/normalization/proposals/{review.id}/review", json=payload)
    assert res.status_code == 400
    assert "does not exist in the loaded reference taxonomy" in res.json()["detail"]

def test_human_review_override_with_valid_nco_code(client: TestClient, db_session: Session):
    """POST /api/normalization/proposals/{id}/review should support overriding with a valid NCO code."""
    review = TitleMappingReview(
        raw_title="IT Operations Clerk",
        normalized_title="it operations clerk",
        source_system="NCS_FEED",
        proposed_nco_code="7421.0301",  # Wrong initial proposal
        proposed_canonical_title="Solar PV Installation & Maintenance Technician",
        match_method="TOKEN_OVERLAP",
        confidence=55.0,
        match_rationale="Ambiguous match",
        status="PROPOSED",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    # Reviewer overrides to Computer Operations (3511.0101)
    payload = {
        "decision": "OVERRIDDEN",
        "override_nco_code": "3511.0101",
        "reviewer_note": "Re-classified from Clean Tech to IT Operations based on job duties.",
    }
    res = client.post(f"/api/normalization/proposals/{review.id}/review", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["assigned_nco_code"] == "3511.0101"
    assert data["canonical_title"] == "Computer Operations & Data Processing Specialist"

def test_import_nco_reference_csv(client: TestClient):
    """POST /api/occupations/reference/import should ingest external NCO CSV taxonomy records."""
    csv_content = """nco_code,canonical_title,division_code,division_title,sub_major_code,sub_major_title,minor_code,minor_title,unit_group_code,unit_group_title,description,aliases
8121.0100,Metal Ore and Alloy Furnace Operator,8,Plant and Machine Operators and Assemblers,81,Stationary Plant and Machine Operators,812,Metal Processing Plant Operators,8121,Metal Smelting Converting and Refining Operator,Operates metal smelting furnaces,Smelter Operator|Blast Furnace Attendant
"""
    files = {"file": ("new_nco.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/occupations/reference/import?source_label=OFFICIAL_DGE", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["occupations_imported"] == 1
    assert data["aliases_imported"] == 2

    # Verify newly imported occupation is searchable
    check_res = client.get("/api/occupations/reference/8121.0100")
    assert check_res.status_code == 200
    assert "Smelter Operator" in check_res.json()["aliases"]
