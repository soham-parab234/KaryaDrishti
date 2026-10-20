"""Automated tests for demand–supply gap calculation, evidence evaluation, and aggregation."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.analytics import (
    DemandObservation,
    QualifiedSupplyEstimate,
    TrainingCapacityOutcome,
)
from backend.app.models.occupation import TitleMappingReview
from backend.app.models.ingestion import IngestedPostingRecord
from backend.app.services.gap_calculator import (
    calculate_absolute_gap,
    calculate_gap_rate,
    assess_evidence_compatibility,
)

def test_basic_arithmetic_positive_gap_shortage():
    """Verify Master R&D Section 8 absolute gap and gap rate arithmetic for shortage."""
    demand = 680
    supply = 420
    gap = calculate_absolute_gap(demand, supply)
    assert gap == 260

    rate, zero_note = calculate_gap_rate(demand, supply)
    assert rate == 38.2
    assert zero_note is None

def test_basic_arithmetic_negative_gap_oversupply():
    """Verify Master R&D Section 8 absolute gap and gap rate arithmetic for oversupply."""
    demand = 1250
    supply = 1480
    gap = calculate_absolute_gap(demand, supply)
    assert gap == -230

    rate, zero_note = calculate_gap_rate(demand, supply)
    assert rate == -18.4
    assert zero_note is None

def test_zero_demand_handling():
    """Verify zero demand suppresses gap rate and returns an explicit explanation."""
    demand = 0
    supply = 50
    gap = calculate_absolute_gap(demand, supply)
    assert gap == -50

    rate, zero_note = calculate_gap_rate(demand, supply)
    assert rate is None
    assert zero_note is not None
    assert "division by zero is mathematically suppressed" in zero_note

def test_missing_supply_evidence_assessment():
    """Missing qualified supply must suppress gap calculation and set MISSING_SUPPLY."""
    assessment = assess_evidence_compatibility(
        demand_val=500,
        demand_period="2026-10",
        demand_district="MH_PUN",
        demand_status="PILOT_BASELINE",
        supply_val=None,
        supply_period=None,
        supply_district=None,
        supply_status=None,
    )
    assert assessment.evidence_status == "MISSING_SUPPLY"
    assert assessment.is_suitable_for_planning is False
    assert any("Qualified supply estimate is missing" in lim for lim in assessment.limitations)

def test_missing_demand_evidence_assessment():
    """Missing observed demand must suppress gap calculation and set MISSING_DEMAND."""
    assessment = assess_evidence_compatibility(
        demand_val=None,
        demand_period=None,
        demand_district=None,
        demand_status=None,
        supply_val=400,
        supply_period="2026-10",
        supply_district="MH_PUN",
        supply_status="PILOT_BASELINE",
    )
    assert assessment.evidence_status == "MISSING_DEMAND"
    assert assessment.is_suitable_for_planning is False
    assert any("Observed demand signal is missing" in lim for lim in assessment.limitations)

def test_incompatible_reporting_periods():
    """Mismatched reporting periods must suppress calculation to prevent misleading findings."""
    assessment = assess_evidence_compatibility(
        demand_val=600,
        demand_period="2026-10",
        demand_district="MH_PUN",
        demand_status="PILOT_BASELINE",
        supply_val=400,
        supply_period="2026-09",  # Different month!
        supply_district="MH_PUN",
        supply_status="PILOT_BASELINE",
    )
    assert assessment.evidence_status == "INCOMPATIBLE_PERIOD_OR_GEOGRAPHY"
    assert assessment.is_suitable_for_planning is False
    assert any("Temporal/Geographic mismatch" in lim for lim in assessment.limitations)

def test_incompatible_geography_districts():
    """Mismatched districts must suppress calculation to prevent misleading findings."""
    assessment = assess_evidence_compatibility(
        demand_val=600,
        demand_period="2026-10",
        demand_district="MH_PUN",
        demand_status="PILOT_BASELINE",
        supply_val=400,
        supply_period="2026-10",
        supply_district="MH_NSK",  # Different district!
        supply_status="PILOT_BASELINE",
    )
    assert assessment.evidence_status == "INCOMPATIBLE_PERIOD_OR_GEOGRAPHY"
    assert assessment.is_suitable_for_planning is False

def test_unresolved_occupation_mappings_reported(client: TestClient, db_session: Session):
    """Unapproved postings must be excluded from confirmed demand and reported in limitations."""
    # Create an observation with 5 excluded unresolved postings
    obs = DemandObservation(
        nco_code="7421.0301",
        district_code="MH_TEST_UNRESOLVED",
        reporting_period="2026-10",
        demand_value=100,
        unit="OBSERVED_POSTINGS",
        source_system="NCS_FEED",
        observation_method="AGGREGATED",
        data_status="PILOT_BASELINE",
        unresolved_postings_count=5,
        rejected_postings_count=2,
    )
    db_session.add(obs)
    db_session.commit()

    # Query gap detail
    res = client.get(
        "/api/analytics/gaps/detail?nco_code=7421.0301&district_code=MH_TEST_UNRESOLVED&reporting_period=2026-10"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["unresolved_postings_count"] == 5
    assert data["rejected_postings_count"] == 2
    assert any("5 unapproved job posting(s) excluded" in lim for lim in data["limitations"])
    assert any("2 job posting(s) excluded due to rejected" in lim for lim in data["limitations"])

def test_synthetic_data_classification_disclosure():
    """Datasets containing synthetic demonstration records must disclose synthetic status."""
    assessment = assess_evidence_compatibility(
        demand_val=300,
        demand_period="2026-10",
        demand_district="MH_PUN",
        demand_status="SYNTHETIC_DEMO",
        supply_val=250,
        supply_period="2026-10",
        supply_district="MH_PUN",
        supply_status="PILOT_BASELINE",
    )
    assert assessment.combined_data_status == "SYNTHETIC_DEMO"
    assert any("synthetic demonstration data" in lim for lim in assessment.limitations)

def test_query_gaps_endpoint_seeded_baseline(client: TestClient):
    """GET /api/analytics/gaps should return the seeded baseline gap indicators."""
    res = client.get("/api/analytics/gaps?district_code=MH_PUN&reporting_period=2026-10")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 3

    # Check Solar PV in Pune: Demand=680, Supply=420, Gap=+260, Gap Rate=38.2%
    solar = next((item for item in data if item["nco_code"] == "7421.0301"), None)
    assert solar is not None
    assert solar["demand_value"] == 680
    assert solar["qualified_supply_value"] == 420
    assert solar["absolute_gap"] == 260
    assert solar["gap_rate_pct"] == 38.2
    assert solar["evidence_status"] == "CALCULATED"
    assert solar["is_suitable_for_planning"] is True

def test_gap_detail_audit_endpoint(client: TestClient):
    """GET /api/analytics/gaps/detail should return full evidence audit and capacity separation."""
    res = client.get(
        "/api/analytics/gaps/detail?nco_code=7421.0301&district_code=MH_PUN&reporting_period=2026-10"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["nco_code"] == "7421.0301"
    assert data["canonical_title"] == "Solar PV Installation & Maintenance Technician"
    assert data["division_code"] == "7"
    assert data["demand_value"] == 680
    assert data["supply_value"] == 420
    assert data["absolute_gap"] == 260
    assert data["sanctioned_training_seats"] == 450
    assert "represent approved institutional intake capacity, NOT active available workers" in data["training_capacity_caveat"]
    assert "Absolute Gap = Demand − Qualified Supply" in data["formula_used"]
    assert data["is_suitable_for_planning"] is True

def test_query_gaps_empty_dataset_returns_empty_list(client: TestClient):
    """Querying gaps for an unobserved district should return an empty list gracefully."""
    res = client.get("/api/analytics/gaps?district_code=MH_UNKNOWN_NONEXISTENT")
    assert res.status_code == 200
    assert res.json() == []

def test_duplicate_observations_upsert_idempotent(client: TestClient):
    """POST /api/analytics/demand should update existing observation if identical key exists."""
    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "reporting_period": "2026-11",
        "demand_value": 700,
        "unit": "OBSERVED_POSTINGS",
        "source_system": "NCS_FEED",
        "observation_method": "MONTHLY_CRAWL",
        "data_status": "PILOT_BASELINE",
        "limitations": "Initial observation",
    }
    # First post creates record
    res1 = client.post("/api/analytics/demand", json=payload)
    assert res1.status_code == 201
    assert res1.json()["demand_value"] == 700

    # Second post with modified demand_value updates rather than creating duplicate
    payload["demand_value"] = 725
    res2 = client.post("/api/analytics/demand", json=payload)
    assert res2.status_code == 201
    assert res2.json()["demand_value"] == 725
    assert res2.json()["id"] == res1.json()["id"]

def test_aggregate_demand_from_postings_excludes_unapproved(client: TestClient, db_session: Session):
    """POST /api/analytics/demand/aggregate-from-postings must only include APPROVED reviews."""
    # Create posting 1: APPROVED (vacancy_count = 3)
    p1 = IngestedPostingRecord(
        batch_id="BATCH-TEST-AGG",
        posting_id="PST-AGG-01",
        raw_title="Solar Rooftop Technician",
        district_code="MH_AGG_DIST",
        observation_date="2026-10-15",
        source_system="NCS_FEED",
        vacancy_count=3,
    )
    db_session.add(p1)
    db_session.flush()

    r1 = TitleMappingReview(
        posting_record_id=p1.id,
        batch_id="BATCH-TEST-AGG",
        raw_title=p1.raw_title,
        normalized_title="solar rooftop technician",
        source_system="NCS_FEED",
        proposed_nco_code="7421.0301",
        match_method="EXACT_ALIAS",
        confidence=98.0,
        match_rationale="Exact verified alias",
        status="APPROVED",  # APPROVED!
    )
    db_session.add(r1)

    # Create posting 2: PROPOSED / UNAPPROVED (vacancy_count = 5)
    p2 = IngestedPostingRecord(
        batch_id="BATCH-TEST-AGG",
        posting_id="PST-AGG-02",
        raw_title="Solar Helper Junior",
        district_code="MH_AGG_DIST",
        observation_date="2026-10-16",
        source_system="NCS_FEED",
        vacancy_count=5,
    )
    db_session.add(p2)
    db_session.flush()

    r2 = TitleMappingReview(
        posting_record_id=p2.id,
        batch_id="BATCH-TEST-AGG",
        raw_title=p2.raw_title,
        normalized_title="solar helper junior",
        source_system="NCS_FEED",
        proposed_nco_code="7421.0301",
        match_method="TOKEN_OVERLAP",
        confidence=50.0,
        match_rationale="Weak token overlap",
        status="PROPOSED",  # UNAPPROVED!
    )
    db_session.add(r2)
    db_session.commit()

    # Trigger aggregation
    agg_res = client.post("/api/analytics/demand/aggregate-from-postings?batch_id=BATCH-TEST-AGG")
    assert agg_res.status_code == 200
    agg_data = agg_res.json()
    assert agg_data["total_approved_postings_aggregated"] == 3  # Only p1 vacancies
    assert agg_data["unresolved_postings_excluded"] >= 1       # p2 excluded

    # Verify the created demand observation in DB
    obs = (
        db_session.query(DemandObservation)
        .filter(
            DemandObservation.nco_code == "7421.0301",
            DemandObservation.district_code == "MH_AGG_DIST",
            DemandObservation.reporting_period == "2026-10",
        )
        .first()
    )
    assert obs is not None
    assert obs.demand_value == 3  # Confirmed demand is only 3, not 8!
    assert obs.unresolved_postings_count >= 1
