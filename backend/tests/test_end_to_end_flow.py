"""
End-to-End Integration Test Suite for LMIS Forecasting Engine (Phase 7).

Verifies the complete analytical data flow using the conftest client fixture:
1. Ingest CSV batch into database
2. Normalization & Human Review Workflow
3. Demand-Supply Gap Arithmetic & Provenance Labeling
4. Chronological Forecasting & Holdout Evaluation (Leakage Prevention)
5. Rule-Based Early Warning Alerts
6. Training-Seat Policy Scenario Simulation
"""

from fastapi.testclient import TestClient


def test_full_e2e_pipeline_workflow(client: TestClient):
    """
    Simulates the end-to-end data pipeline from raw employer posting CSV
    to gap calculation, forecasting, alert generation, and scenario planning.
    """
    # Step 1: Ensure baseline analytics data is present
    seed_resp = client.post("/api/analytics/seed-baseline")
    assert seed_resp.status_code == 200
    assert seed_resp.json()["provenance"] == "SYNTHETIC_DEMO"

    # Step 2: Seed multi-period forecasting history
    hist_resp = client.post("/api/forecasting/seed-history")
    assert hist_resp.status_code == 200
    assert hist_resp.json()["status"] == "COMPLETED"
    assert hist_resp.json()["demand_points_seeded"] >= 16

    # Step 3: Ingest a new raw job postings CSV batch
    csv_content = (
        "posting_id,raw_title,district_code,observation_date,source_system,vacancy_count\n"
        "PST-E2E-001,Solar Rooftop Technician,MH_PUN,2026-10-15,NCS_FEED,3\n"
        "PST-E2E-002,CNC Milling Machine Operator,MH_NSK,2026-10-16,PORTAL_SCRAPE,2\n"
    )
    files = {"file": ("october_postings.csv", csv_content.encode("utf-8"), "text/csv")}
    import_resp = client.post("/api/ingestion/import", files=files)
    assert import_resp.status_code == 201
    import_data = import_resp.json()
    assert import_data["status"] == "COMPLETED"
    assert import_data["imported_rows"] == 2
    batch_id = import_data["batch_id"]

    # Step 4: Run batch normalization to create review queue items
    norm_resp = client.post(f"/api/normalization/process-batch/{batch_id}")
    assert norm_resp.status_code == 200
    norm_data = norm_resp.json()
    assert norm_data["total_postings_processed"] == 2
    assert norm_data["proposals_created"] == 2

    # Query proposals endpoint
    prop_resp = client.get(f"/api/normalization/proposals?batch_id={batch_id}")
    assert prop_resp.status_code == 200
    proposals = prop_resp.json()
    assert len(proposals) == 2

    solar_prop = next((p for p in proposals if p["raw_title"] == "Solar Rooftop Technician"), None)
    assert solar_prop is not None
    assert solar_prop["proposed_nco_code"] == "7421.0301"

    # Step 5: Planning officer reviews and approves mapping
    review_resp = client.post(
        f"/api/normalization/proposals/{solar_prop['id']}/review",
        json={
            "decision": "APPROVED",
            "reviewer_note": "Verified match with Solar PV technician NCO standard.",
        },
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "APPROVED"

    # Step 6: Query demand-supply gap ledger for Pune district for current period 2026-10
    gap_resp = client.get("/api/analytics/gaps?district_code=MH_PUN&reporting_period=2026-10")
    assert gap_resp.status_code == 200
    gaps = gap_resp.json()
    assert len(gaps) >= 1
    solar_gap = next((g for g in gaps if g["nco_code"] == "7421.0301"), None)
    assert solar_gap is not None
    assert solar_gap["data_status"] == "SYNTHETIC_DEMO"
    assert solar_gap["demand_value"] == 680
    assert solar_gap["qualified_supply_value"] == 420
    assert solar_gap["absolute_gap"] == 260
    assert solar_gap["gap_rate_pct"] == 38.2

    # Step 7: Run forecasting engine on Pune solar PV time series
    forecast_resp = client.post(
        "/api/forecasting/generate",
        json={
            "nco_code": "7421.0301",
            "district_code": "MH_PUN",
            "target_series": "DEMAND",
            "forecast_horizon_months": 3,
        },
    )
    assert forecast_resp.status_code == 200
    forecast_data = forecast_resp.json()
    assert forecast_data["nco_code"] == "7421.0301"
    assert forecast_data["evaluation"]["evaluation_status"] == "EVALUATED"
    assert len(forecast_data["forecast_points"]) == 3
    for pt in forecast_data["forecast_points"]:
        assert pt["lower_bound"] <= pt["forecast_value"] <= pt["upper_bound"]
        assert pt["lower_bound"] >= 0.0

    # Holdout evaluation without leakage
    evaluation = forecast_data["evaluation"]
    assert evaluation is not None
    assert evaluation["evaluation_status"] == "EVALUATED"
    assert evaluation["holdout_periods_count"] == 3
    assert evaluation["baseline_mae"] is not None
    assert evaluation["baseline_mae"] >= 0.0

    # Step 8: Trigger early warning alerts evaluation
    alerts_resp = client.get("/api/alerts?district_code=MH_PUN")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) >= 1
    solar_alert = next((a for a in alerts if a["nco_code"] == "7421.0301" and a["alert_type"] == "SHORTAGE_RISK"), None)
    assert solar_alert is not None
    assert solar_alert["severity"] == "CRITICAL"
    assert solar_alert["alert_type"] == "SHORTAGE_RISK"
    assert solar_alert["threshold_type"] == "CONFIGURABLE_PROTOTYPE_DEFAULT"
    assert "data_status" in solar_alert

    # Also verify that forecast-driven projected alert is generated and kept distinct
    proj_alert = next((a for a in alerts if a["nco_code"] == "7421.0301" and a["alert_type"] == "PROJECTED_SHORTAGE_RISK"), None)
    assert proj_alert is not None
    assert proj_alert["threshold_type"] == "FORECAST_PROJECTION_RULE"

    # Step 9: Simulate training seat expansion in Scenario Planner
    scenario_resp = client.post(
        "/api/scenarios/calculate",
        json={
            "nco_code": "7421.0301",
            "district_code": "MH_PUN",
            "reporting_period": "2026-10",
            "baseline_gap": 260.0,
            "proposed_additional_seats": 500,
            "enrolment_rate_pct": 85.0,
            "completion_rate_pct": 80.0,
            "local_entry_rate_pct": 75.0,
            "trainee_trainer_ratio": 20,
            "estimated_cost_per_seat_inr": 18000.0,
        },
    )
    assert scenario_resp.status_code == 200
    scenario_res = scenario_resp.json()
    assert scenario_res["scenario_entrants"] == 255.0
    assert scenario_res["residual_gap"] == 5.0
    assert scenario_res["estimated_budget_inr"] == 9_000_000.0
    assert scenario_res["estimated_trainers_required"] == 25
    assert scenario_res["is_scenario_only"] is True
    assert "formula_used" in scenario_res

    # Step 10: Decision Intelligence recommendations generated from evidence (Phase 10)
    recs_resp = client.get("/api/recommendations?district_code=MH_PUN")
    assert recs_resp.status_code == 200
    recs_data = recs_resp.json()
    assert recs_data["total_recommendations"] > 0
    assert len(recs_data["items"]) > 0
    for r in recs_data["items"]:
        assert r["recommendation_type"] in {
            "TRAINING_CAPACITY_EXPANSION",
            "CURRICULUM_MODERNIZATION_OR_PIVOT",
            "APPRENTICESHIP_INDUSTRY_TIE_UP",
            "DATA_COLLECTION_AUDIT",
        }
        assert 0.0 <= r["feasibility_score"] <= 1.0

    # Step 11: Data integration connectors and institutional supply adapter (Phase 11)
    connectors_resp = client.get("/api/ingestion/connectors")
    assert connectors_resp.status_code == 200
    connectors = connectors_resp.json()
    assert len(connectors) == 5
    assert any(c["connector_id"] == "TRAINING_SUPPLY_CSV_ADAPTER" for c in connectors)

    # Step 12: Governance audit logging and mathematical explainability (Phase 12)
    audit_resp = client.get("/api/governance/audit-logs")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) > 0
    assert any(l["event_type"] in {"INGESTION_BATCH_IMPORT", "OCCUPATION_MAPPING_REVIEW"} for l in logs)

    exp_resp = client.get("/api/governance/explainability/forecast_intervals")
    assert exp_resp.status_code == 200
    exp_doc = exp_resp.json()
    assert "sigma_h^2" in exp_doc["mathematical_formula"]

    # Step 13: End-to-end pipeline recompute refreshes all dependent intelligence (Phase 13)
    recompute_resp = client.post("/api/analytics/recompute-pipeline")
    assert recompute_resp.status_code == 200
    rec_data = recompute_resp.json()
    assert rec_data["forecasts_recomputed"] > 0
    assert rec_data["recommendations_generated"] > 0
    assert rec_data["alerts_evaluated"] > 0

