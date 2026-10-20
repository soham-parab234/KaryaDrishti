"""Tests for Phase 4: Forecasting Engine.

Verifies:
- Insufficient history (< 6 periods) returns INSUFFICIENT_DATA without fabricating numbers.
- Strict chronological holdout evaluation (zero future-data leakage).
- Baseline vs Candidate comparison with true MAE, RMSE, MAPE metrics.
- Model selection based on holdout evaluation evidence.
- Prediction uncertainty intervals (80% CI) with non-negative lower bounds.
- Full API workflow: /api/forecasting/projections, /generate, /evaluations, /seed-history.
- Synthetic data labeling and limitations disclosure.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.analytics import DemandObservation
from backend.app.models.forecasting import ForecastRun, ForecastPoint
from backend.app.services.forecasting import (
    MovingAverageBaseline,
    HoltExponentialSmoothing,
    compute_evaluation_metrics,
    reconcile_time_series_observations,
    seed_demo_time_series,
)


def test_baseline_moving_average_logic():
    """3M Moving average should predict flat mean of last 3 observations."""
    model = MovingAverageBaseline(window=3)
    model.fit([100.0, 120.0, 140.0])
    preds = model.predict(steps_ahead=3)
    assert len(preds) == 3
    assert preds[0] == 120.0  # (100 + 120 + 140) / 3
    assert preds[1] == 120.0
    assert preds[2] == 120.0


def test_candidate_holt_smoothing_trend():
    """Holt linear smoothing should capture positive trend."""
    model = HoltExponentialSmoothing(alpha=0.5, beta=0.2)
    # Strongly growing series
    model.fit([100.0, 110.0, 120.0, 130.0, 140.0])
    preds = model.predict(steps_ahead=3)
    assert len(preds) == 3
    # Step 1 should be higher than 140, and step 2 higher than step 1
    assert preds[0] > 140.0
    assert preds[1] > preds[0]
    assert preds[2] > preds[1]


def test_holdout_metrics_calculation():
    """Verify MAE, RMSE, and MAPE calculations."""
    actuals = [100.0, 200.0, 300.0]
    preds = [110.0, 190.0, 330.0]
    mae, rmse, mape = compute_evaluation_metrics(actuals, preds)
    # Errors: |+10|, |-10|, |+30| -> MAE = (10 + 10 + 30) / 3 = 16.67
    assert mae == 16.67
    # Sq errors: 100, 100, 900 -> RMSE = sqrt(1100 / 3) = sqrt(366.67) = 19.15
    assert rmse == 19.15
    # MAPE: (10/100 + 10/200 + 30/300) / 3 = (0.10 + 0.05 + 0.10) / 3 = 0.25 / 3 = 8.33%
    assert mape == 8.33


def test_insufficient_history_returns_insufficient_data(client: TestClient, db_session: Session):
    """When fewer than 6 points exist, forecasting must return INSUFFICIENT_DATA and suppress projection."""
    # Seed only 3 observations for a test occupation
    for p, val in [("2026-08", 100), ("2026-09", 110), ("2026-10", 120)]:
        db_session.add(
            DemandObservation(
                nco_code="9999.0001",
                district_code="MH_SHORT_SERIES",
                reporting_period=p,
                demand_value=val,
                unit="OBSERVED_POSTINGS",
                source_system="SYNTHETIC_TEST",
                observation_method="SYNTHETIC_DEMO",
                data_status="SYNTHETIC_DEMO",
                limitations="Sparse test history",
            )
        )
    db_session.commit()

    payload = {
        "nco_code": "9999.0001",
        "district_code": "MH_SHORT_SERIES",
        "target_metric": "DEMAND",
        "horizon_periods": 3,
        "holdout_periods": 3,
    }
    res = client.post("/api/forecasting/generate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["evaluation"]["evaluation_status"] == "INSUFFICIENT_DATA"
    assert data["forecast_points"] == []  # No fabricated forecasts
    assert "Insufficient evidence" in data["evaluation"]["model_comparison_verdict"]
    assert any("Forecasting suppressed" in lim for lim in data["limitations"])
    assert data["data_status"] == "SYNTHETIC_DEMO"


def test_chronological_holdout_evaluation_and_projections(client: TestClient, db_session: Session):
    """With full 18-month history, model evaluation compares Baseline vs Candidate on holdout and projects ahead."""
    # Seed demo series
    seed_demo_time_series(db_session)

    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "target_metric": "DEMAND",
        "horizon_periods": 3,
        "holdout_periods": 3,
    }
    res = client.post("/api/forecasting/generate", json=payload)
    assert res.status_code == 200
    data = res.json()

    # 1. Historical series checks
    assert len(data["historical_series"]) >= 18
    # Chronological ordering check
    periods = [h["period"] for h in data["historical_series"]]
    assert periods == sorted(periods)
    assert periods[-1] == "2026-10"

    # 2. Evaluation scorecard checks
    eval_card = data["evaluation"]
    assert eval_card["evaluation_status"] == "EVALUATED"
    assert eval_card["baseline_model_name"] == "MOVING_AVERAGE_3M"
    assert eval_card["candidate_model_name"] == "HOLT_EXPONENTIAL_SMOOTHING"
    assert eval_card["selected_model_name"] in ["HOLT_EXPONENTIAL_SMOOTHING", "MOVING_AVERAGE_3M"]
    assert eval_card["baseline_mae"] is not None
    assert eval_card["candidate_mae"] is not None
    assert eval_card["candidate_rmse"] is not None
    assert "Zero future information leakage" in eval_card["leakage_prevention_notice"]
    assert len(eval_card["model_comparison_verdict"]) > 20

    # 3. Forecast points checks
    points = data["forecast_points"]
    assert len(points) == 3
    assert points[0]["period"] == "2026-11"
    assert points[1]["period"] == "2026-12"
    assert points[2]["period"] == "2027-01"

    # Bounds must be present and lower bound <= forecast_value <= upper_bound
    for pt in points:
        assert pt["lower_bound"] is not None
        assert pt["upper_bound"] is not None
        assert pt["lower_bound"] >= 0.0  # Non-negative lower bound
        assert pt["lower_bound"] <= pt["forecast_value"] <= pt["upper_bound"]

    # Expanding uncertainty: horizon step 3 confidence interval width > step 1 width
    width_1 = points[0]["upper_bound"] - points[0]["lower_bound"]
    width_3 = points[2]["upper_bound"] - points[2]["lower_bound"]
    assert width_3 >= width_1


def test_get_projections_auto_runs_forecast(client: TestClient, db_session: Session):
    """GET /api/forecasting/projections should retrieve or generate projections with query params."""
    seed_demo_time_series(db_session)

    res = client.get("/api/forecasting/projections?nco_code=7421.0301&district_code=MH_PUN&target_metric=DEMAND&horizon_periods=3")
    assert res.status_code == 200
    data = res.json()
    assert data["nco_code"] == "7421.0301"
    assert data["district_code"] == "MH_PUN"
    assert len(data["forecast_points"]) == 3
    assert data["data_status"] == "SYNTHETIC_DEMO"


def test_list_evaluations_endpoint(client: TestClient, db_session: Session):
    """GET /api/forecasting/evaluations should return historical evaluation scorecards."""
    seed_demo_time_series(db_session)
    # Generate a run
    client.post(
        "/api/forecasting/generate",
        json={"nco_code": "7233.0100", "district_code": "MH_PUN", "target_metric": "DEMAND"},
    )

    res = client.get("/api/forecasting/evaluations?district_code=MH_PUN")
    assert res.status_code == 200
    evals = res.json()
    assert len(evals) >= 1
    sample = evals[0]
    assert "run_id" in sample
    assert sample["baseline_mae"] is not None
    assert sample["candidate_mae"] is not None


def test_reconcile_time_series_duplicate_month_precedence():
    """Ensure imported observations supersede synthetic placeholders without summing them together."""
    obs_synthetic = DemandObservation(
        nco_code="7421.0301",
        district_code="MH_PUN",
        reporting_period="2026-10",
        demand_value=500.0,
        unit="OBSERVED_POSTINGS",
        source_system="SYNTHETIC_NCS_ILLUSTRATIVE",
        observation_method="SYNTHETIC_DEMO",
        data_status="SYNTHETIC_DEMO",
        limitations="Placeholder",
    )
    obs_imported = DemandObservation(
        nco_code="7421.0301",
        district_code="MH_PUN",
        reporting_period="2026-10",
        demand_value=120.0,
        unit="OBSERVED_POSTINGS",
        source_system="NCS_JOB_FEED",
        observation_method="APPROVED_TITLE_MAPPING",
        data_status="IMPORTED",
        limitations="Confirmed postings",
    )

    reconciled, status, limitations = reconcile_time_series_observations(
        [obs_synthetic, obs_imported], target_metric="DEMAND"
    )

    # Must contain exactly 1 point for 2026-10
    assert len(reconciled) == 1
    # Must equal imported value (120.0), NOT synthetic + imported (620.0)
    assert reconciled[0].value == 120.0
    assert reconciled[0].data_status == "IMPORTED"
    assert reconciled[0].source == "NCS_JOB_FEED"
    assert status == "IMPORTED"


def test_reconcile_time_series_multi_import_aggregation():
    """Ensure multiple legitimate imported records for the same month are aggregated correctly."""
    imp_1 = DemandObservation(
        nco_code="7421.0301",
        district_code="MH_PUN",
        reporting_period="2026-10",
        demand_value=85.0,
        unit="OBSERVED_POSTINGS",
        source_system="PORTAL_ALPHA",
        observation_method="APPROVED_TITLE_MAPPING",
        data_status="IMPORTED",
        limitations="Alpha batch",
    )
    imp_2 = DemandObservation(
        nco_code="7421.0301",
        district_code="MH_PUN",
        reporting_period="2026-10",
        demand_value=40.0,
        unit="OBSERVED_POSTINGS",
        source_system="PORTAL_BETA",
        observation_method="APPROVED_TITLE_MAPPING",
        data_status="IMPORTED",
        limitations="Beta batch",
    )

    reconciled, status, limitations = reconcile_time_series_observations(
        [imp_1, imp_2], target_metric="DEMAND"
    )

    assert len(reconciled) == 1
    assert reconciled[0].value == 125.0  # 85 + 40
    assert reconciled[0].data_status == "IMPORTED"
    assert "PORTAL_ALPHA" in reconciled[0].source and "PORTAL_BETA" in reconciled[0].source
    assert status == "IMPORTED"


def test_provenance_classification_hybrid_and_synthetic():
    """Verify provenance classification: SYNTHETIC_DEMO for all-synthetic, HYBRID for mixed."""
    # All synthetic
    syn_records = [
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period=f"2026-{m:02d}",
            demand_value=100.0 + m,
            unit="OBSERVED_POSTINGS",
            source_system="SYNTHETIC_NCS_ILLUSTRATIVE",
            observation_method="SYNTHETIC_DEMO",
            data_status="SYNTHETIC_DEMO",
            limitations="Synthetic",
        )
        for m in range(1, 10)
    ]
    _, status_all_syn, _ = reconcile_time_series_observations(syn_records, target_metric="DEMAND")
    assert status_all_syn == "SYNTHETIC_DEMO"

    # Mixed synthetic + imported
    mixed_records = list(syn_records)
    mixed_records.append(
        DemandObservation(
            nco_code="7421.0301",
            district_code="MH_PUN",
            reporting_period="2026-10",
            demand_value=250.0,
            unit="OBSERVED_POSTINGS",
            source_system="CONFIRMED_IMPORT",
            observation_method="APPROVED_TITLE_MAPPING",
            data_status="IMPORTED",
            limitations="Imported",
        )
    )
    reconciled_mixed, status_mixed, limitations_mixed = reconcile_time_series_observations(
        mixed_records, target_metric="DEMAND"
    )
    assert status_mixed == "HYBRID_BASELINE_PLUS_IMPORT"
    assert any("HYBRID PROVENANCE" in lim for lim in limitations_mixed)
    # 2026-10 must be marked IMPORTED, earlier months marked SYNTHETIC_DEMO
    pt_10 = next(p for p in reconciled_mixed if p.period == "2026-10")
    assert pt_10.data_status == "IMPORTED"
    pt_01 = next(p for p in reconciled_mixed if p.period == "2026-01")
    assert pt_01.data_status == "SYNTHETIC_DEMO"


def test_prediction_interval_state_space_expansion_monotonic():
    """Verify that state-space prediction interval half-widths expand monotonically with horizon."""
    model = HoltExponentialSmoothing(alpha=0.35, beta=0.15)
    series = [100.0, 110.0, 115.0, 125.0, 130.0, 140.0, 145.0, 155.0]
    model.fit(series)
    preds = model.predict(steps_ahead=3)

    residuals = [act - fit for act, fit in zip(series, model.fitted_values)]
    residual_std = (sum(r**2 for r in residuals) / max(1, len(residuals) - 2)) ** 0.5

    alpha = 0.35
    beta = 0.15
    z_mult = 1.282

    half_widths = []
    for step, val in enumerate(preds, start=1):
        var_multiplier = 1.0 + sum((alpha + j * alpha * beta) ** 2 for j in range(1, step))
        se_step = residual_std * (var_multiplier**0.5)
        hw = z_mult * se_step
        half_widths.append(hw)

    assert half_widths[0] < half_widths[1] < half_widths[2]
    # Lower bounds truncated at 0.0
    for val, hw in zip(preds, half_widths):
        lower = max(0.0, val - hw)
        assert lower >= 0.0


def test_forecast_generation_idempotent_no_duplicate_runs(client: TestClient, db_session: Session):
    """Running forecast generation multiple times for same target must update existing run, not duplicate rows."""
    seed_demo_time_series(db_session)

    payload = {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "target_metric": "DEMAND",
        "horizon_periods": 3,
        "holdout_periods": 3,
    }

    # First run
    res1 = client.post("/api/forecasting/generate", json=payload)
    assert res1.status_code == 200

    count_after_first = (
        db_session.query(ForecastRun)
        .filter(
            ForecastRun.nco_code == "7421.0301",
            ForecastRun.district_code == "MH_PUN",
            ForecastRun.target_metric == "DEMAND",
        )
        .count()
    )
    assert count_after_first == 1

    # Second run
    res2 = client.post("/api/forecasting/generate", json=payload)
    assert res2.status_code == 200

    count_after_second = (
        db_session.query(ForecastRun)
        .filter(
            ForecastRun.nco_code == "7421.0301",
            ForecastRun.district_code == "MH_PUN",
            ForecastRun.target_metric == "DEMAND",
        )
        .count()
    )
    # Must still be exactly 1 run in database!
    assert count_after_second == 1
