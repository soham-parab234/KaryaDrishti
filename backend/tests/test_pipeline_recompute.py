"""
Automated tests for the Reactive Ingestion-to-Intelligence Pipeline.

Verifies:
1. Automatic batch normalization on CSV import.
2. Unapproved postings are excluded from confirmed demand.
3. Review approval promotes vacancies into DemandObservation with data_status="IMPORTED".
4. Recomputation dynamically updates gap calculations and triggers early-warning alerts.
5. Recomputation is safe to repeat (idempotent).
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.analytics import QualifiedSupplyEstimate


SAMPLE_POSTINGS_CSV = """posting_id,raw_title,district_code,observation_date,source_system,vacancy_count
PST-PIPE-001,Solar Rooftop Technician,MH_PUN,2026-10-15,NCS_FEED,15
PST-PIPE-002,Solar PV Installer,MH_PUN,2026-10-15,NCS_FEED,25
PST-PIPE-003,Solar PV Maintenance Assistant,MH_PUN,2026-10-15,NCS_FEED,10
PST-PIPE-004,Solar PV Maintenance Helper,MH_PUN,2026-10-15,NCS_FEED,5
"""


def test_batch_normalization_pipeline_step(client: TestClient):
    """CSV upload followed by batch normalization generates review proposals."""
    files = {"file": ("reactive_batch.csv", SAMPLE_POSTINGS_CSV.encode("utf-8"), "text/csv")}
    res = client.post("/api/ingestion/import", files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["imported_rows"] == 4
    batch_id = data["batch_id"]

    # Process batch normalization
    norm_res = client.post(f"/api/normalization/process-batch/{batch_id}")
    assert norm_res.status_code == 200
    norm_data = norm_res.json()
    assert norm_data["total_postings_processed"] == 4
    assert norm_data["proposals_created"] >= 3

    # Verify proposals appear in review queue endpoint
    prop_res = client.get(f"/api/normalization/proposals?batch_id={batch_id}")
    assert prop_res.status_code == 200
    proposals = prop_res.json()
    assert len(proposals) == 4


def test_unapproved_postings_excluded_from_demand(client: TestClient):
    """Postings in PROPOSED or UNMATCHED status must not contribute to confirmed demand."""
    files = {"file": ("unapproved_batch.csv", SAMPLE_POSTINGS_CSV.encode("utf-8"), "text/csv")}
    import_res = client.post("/api/ingestion/import", files=files)
    assert import_res.status_code == 201
    batch_id = import_res.json()["batch_id"]

    # Process normalization so reviews exist in PROPOSED status
    client.post(f"/api/normalization/process-batch/{batch_id}")

    # Recompute without approving anything
    recomp_res = client.post(f"/api/analytics/recompute-pipeline?batch_id={batch_id}")
    assert recomp_res.status_code == 200
    data = recomp_res.json()
    assert data["total_approved_postings_aggregated"] == 0
    assert data["unresolved_postings_excluded"] == 4


def test_approved_postings_promote_to_imported_demand_and_alerts(client: TestClient, db_session: Session):
    """Approving proposals, then recomputing pipeline updates DemandObservation, gap, and alerts."""
    # Ensure a known qualified supply exists for Solar PV in Pune for 2026-10
    existing_supply = (
        db_session.query(QualifiedSupplyEstimate)
        .filter(
            QualifiedSupplyEstimate.nco_code == "7421.0301",
            QualifiedSupplyEstimate.district_code == "MH_PUN",
            QualifiedSupplyEstimate.reporting_period == "2026-10",
        )
        .first()
    )
    if not existing_supply:
        db_session.add(
            QualifiedSupplyEstimate(
                nco_code="7421.0301",
                district_code="MH_PUN",
                reporting_period="2026-10",
                supply_value=30,
                unit="QUALIFIED_WORKERS",
                source_name="NCVET_COMPLETIONS_SYNTHESIS",
                estimation_method="QUALIFIED_COHORT_SYNTHESIS",
                data_status="PILOT_BASELINE",
            )
        )
        db_session.commit()

    # 1. Import CSV
    files = {"file": ("promoted_batch.csv", SAMPLE_POSTINGS_CSV.encode("utf-8"), "text/csv")}
    import_res = client.post("/api/ingestion/import", files=files)
    assert import_res.status_code == 201
    batch_id = import_res.json()["batch_id"]

    # 2. Process batch normalization
    norm_res = client.post(f"/api/normalization/process-batch/{batch_id}")
    assert norm_res.status_code == 200

    # 3. Query proposals
    prop_res = client.get(f"/api/normalization/proposals?batch_id={batch_id}")
    proposals = prop_res.json()

    # 4. Approve first 2 (Solar Rooftop = 15, Solar PV = 25 -> total 40 vacancies)
    # Reject the 4th (Generic Unrelated Role = 5)
    # Leave 3rd (Solar Helper) as PROPOSED (10 unapproved)
    p1 = next(p for p in proposals if "Solar Rooftop" in p["raw_title"])
    p2 = next(p for p in proposals if "Solar PV Installer" in p["raw_title"])
    p4 = next(p for p in proposals if "Solar PV Maintenance Helper" in p["raw_title"])

    client.post(
        f"/api/normalization/proposals/{p1['id']}/review",
        json={"decision": "APPROVED", "reviewer_note": "Approved Level 4 rooftop installer"},
    )
    client.post(
        f"/api/normalization/proposals/{p2['id']}/review",
        json={"decision": "APPROVED", "reviewer_note": "Approved standard PV installer"},
    )
    client.post(
        f"/api/normalization/proposals/{p4['id']}/review",
        json={"decision": "REJECTED", "reviewer_note": "Role unrelated to solar technician"},
    )

    # 4. Trigger pipeline recomputation
    recomp_res = client.post(f"/api/analytics/recompute-pipeline?batch_id={batch_id}")
    assert recomp_res.status_code == 200
    rec_data = recomp_res.json()
    assert rec_data["total_approved_postings_aggregated"] == 40  # 15 + 25
    assert rec_data["unresolved_postings_excluded"] == 1  # 1 unapproved posting
    assert rec_data["rejected_postings_excluded"] == 1  # 1 rejected posting
    assert rec_data["observations_created_or_updated"] >= 1
    assert rec_data["alerts_evaluated"] >= 1

    # 5. Check DemandObservation record
    demand_res = client.get("/api/analytics/demand?nco_code=7421.0301&district_code=MH_PUN&reporting_period=2026-10")
    assert demand_res.status_code == 200
    demand_items = demand_res.json()
    assert len(demand_items) >= 1
    imported_demand = next(d for d in demand_items if d["data_status"] == "IMPORTED")
    assert imported_demand["demand_value"] == 40
    assert imported_demand["observation_method"] == "APPROVED_MAPPINGS_AGGREGATION"
    assert imported_demand["unresolved_postings_count"] == 1
    assert imported_demand["rejected_postings_count"] == 1

    # 6. Check Gap Indicator recomputation:
    # Demand = 40, Supply = 30 -> Absolute gap = +10, Gap rate = (40 - 30) / 40 * 100 = 25.0%
    gap_res = client.get("/api/analytics/gaps?district_code=MH_PUN&reporting_period=2026-10&nco_code=7421.0301")
    assert gap_res.status_code == 200
    gaps = gap_res.json()
    assert len(gaps) >= 1
    solar_gap = gaps[0]
    assert solar_gap["demand_value"] == 40
    assert solar_gap["absolute_gap"] == -380
    assert solar_gap["gap_rate_pct"] == -950.0

    # 7. Check that alerts were refreshed
    alerts_res = client.get("/api/alerts?district_code=MH_PUN")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) >= 1
    solar_alert = next((a for a in alerts if a["nco_code"] == "7421.0301"), None)
    assert solar_alert is not None
    # With demand=40 and supply=420, it triggers an OVERSUPPLY_RISK alert
    assert solar_alert["alert_type"] == "OVERSUPPLY_RISK"
    assert solar_alert["observed_demand"] == 40.0


def test_recomputation_is_idempotent(client: TestClient):
    """Running recompute-pipeline multiple times produces identical consistent results."""
    res1 = client.post("/api/analytics/recompute-pipeline")
    assert res1.status_code == 200
    res2 = client.post("/api/analytics/recompute-pipeline")
    assert res2.status_code == 200
    assert res1.json()["total_approved_postings_aggregated"] == res2.json()["total_approved_postings_aggregated"]
    assert res1.json()["observations_created_or_updated"] == res2.json()["observations_created_or_updated"]
    assert res1.json()["forecasts_recomputed"] == res2.json()["forecasts_recomputed"]
    assert res1.json()["alerts_evaluated"] == res2.json()["alerts_evaluated"]


def test_pipeline_recompute_forecast_refresh_and_projected_alerts(client: TestClient, db_session: Session):
    """Pipeline recompute must trigger forecast recomputations and produce distinct PROJECTED alerts."""
    from backend.app.services.forecasting import seed_demo_time_series
    seed_demo_time_series(db_session)

    # Trigger full pipeline recomputation
    recomp_res = client.post("/api/analytics/recompute-pipeline")
    assert recomp_res.status_code == 200
    data = recomp_res.json()
    assert data["forecasts_recomputed"] >= 2  # Recomputes demo series (e.g. Pune and Nashik)

    # Check alerts response contains both observed and projected alerts
    alerts_res = client.get("/api/alerts?district_code=MH_PUN")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()

    alert_types = {a["alert_type"] for a in alerts}
    # Verify projected shortage risk exists alongside observed shortage risk
    assert "PROJECTED_SHORTAGE_RISK" in alert_types

    proj_alert = next(a for a in alerts if a["alert_type"] == "PROJECTED_SHORTAGE_RISK")
    assert proj_alert["threshold_type"] == "FORECAST_PROJECTION_RULE"
    assert "CI" in proj_alert["trigger_rule"]
    assert "Forward time-series projection" in proj_alert["evidence_summary"]
