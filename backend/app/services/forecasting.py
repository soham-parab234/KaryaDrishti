"""Forecasting Service for LMIS Engine.

Conforms strictly to LMIS Master R&D Section 9:
1. Validates length, frequency, completeness, and chronological order of time series.
2. Enforces strict chronological holdout evaluation (ZERO future-data leakage).
3. Implements transparent baseline (3-month moving average) first.
4. Evaluates candidate model (Holt's Linear Exponential Smoothing).
5. Calculates true holdout error metrics (MAE, RMSE, MAPE).
6. Selects model based on empirical holdout performance, never claiming superiority without evidence.
7. Produces uncertainty intervals (80% CI) derived from residual standard deviation.
8. Distinguishes historical observations from forward projections.
9. Returns explicit INSUFFICIENT_DATA status when time series is too brief (< 6 points).
"""

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.analytics import DemandObservation, QualifiedSupplyEstimate
from backend.app.models.forecasting import ForecastRun, ForecastPoint
from backend.app.models.occupation import NcoOccupation
from backend.app.schemas.forecasting import (
    ForecastPointSchema,
    HistoricalPointSchema,
    ModelEvaluationScorecard,
    ForecastProjectionResponse,
    GenerateForecastRequest,
)


@dataclass
class TimeSeriesObservation:
    period: str  # "YYYY-MM"
    value: float
    source: str
    data_status: str


def parse_period_to_ordinal(period_str: str) -> int:
    """Convert 'YYYY-MM' to a monotonic integer month counter for chronological sorting."""
    parts = period_str.strip().split("-")
    if len(parts) >= 2:
        try:
            return int(parts[0]) * 12 + int(parts[1])
        except ValueError:
            pass
    return 0


def format_ordinal_to_period(ordinal: int) -> str:
    """Convert monotonic integer month counter back to 'YYYY-MM'."""
    year = (ordinal - 1) // 12
    month = ((ordinal - 1) % 12) + 1
    return f"{year:04d}-{month:02d}"


def add_months_to_period(period_str: str, months_to_add: int) -> str:
    """Compute period string after adding N months."""
    ord_val = parse_period_to_ordinal(period_str)
    return format_ordinal_to_period(ord_val + months_to_add)


class MovingAverageBaseline:
    """Transparent baseline model: 3-period moving average."""

    def __init__(self, window: int = 3):
        self.window = window
        self.history: list[float] = []

    def fit(self, series: list[float]) -> "MovingAverageBaseline":
        self.history = list(series)
        return self

    def predict(self, steps_ahead: int) -> list[float]:
        if not self.history:
            return [0.0] * steps_ahead
        w = min(len(self.history), self.window)
        val = sum(self.history[-w:]) / w
        return [round(val, 2)] * steps_ahead


class HoltExponentialSmoothing:
    """Candidate model: Holt's Linear Exponential Smoothing with trend."""

    def __init__(self, alpha: float = 0.35, beta: float = 0.15):
        self.alpha = alpha
        self.beta = beta
        self.level: float = 0.0
        self.trend: float = 0.0
        self.fitted_values: list[float] = []

    def fit(self, series: list[float]) -> "HoltExponentialSmoothing":
        if len(series) < 2:
            self.level = series[0] if series else 0.0
            self.trend = 0.0
            self.fitted_values = [self.level]
            return self

        # Initialize level and trend from first two observations
        self.level = series[0]
        self.trend = series[1] - series[0]
        self.fitted_values = [self.level]

        for y in series[1:]:
            prev_level = self.level
            prev_trend = self.trend
            # Level equation
            self.level = self.alpha * y + (1 - self.alpha) * (prev_level + prev_trend)
            # Trend equation
            self.trend = self.beta * (self.level - prev_level) + (1 - self.beta) * prev_trend
            self.fitted_values.append(prev_level + prev_trend)

        return self

    def predict(self, steps_ahead: int) -> list[float]:
        preds = []
        for h in range(1, steps_ahead + 1):
            pred_val = self.level + h * self.trend
            # Employment demand and qualified supply cannot be negative
            preds.append(round(max(0.0, pred_val), 2))
        return preds


def compute_evaluation_metrics(actuals: list[float], predictions: list[float]) -> tuple[float, float, float]:
    """Compute holdout MAE, RMSE, and MAPE strictly on held-out observations."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0, 0.0, 0.0

    k = len(actuals)
    abs_errors = [abs(a - p) for a, p in zip(actuals, predictions)]
    sq_errors = [(a - p) ** 2 for a, p in zip(actuals, predictions)]
    # Protect against division by zero in MAPE
    pct_errors = [abs(a - p) / max(1.0, abs(a)) for a, p in zip(actuals, predictions)]

    mae = sum(abs_errors) / k
    rmse = math.sqrt(sum(sq_errors) / k)
    mape = (sum(pct_errors) / k) * 100.0

    return round(mae, 2), round(rmse, 2), round(mape, 2)


def reconcile_time_series_observations(
    records: list[DemandObservation] | list[QualifiedSupplyEstimate],
    target_metric: str = "DEMAND",
) -> tuple[list[TimeSeriesObservation], str, list[str]]:
    """Reconcile monthly time-series observations with explicit source precedence and aggregation.

    Rules strictly enforced:
    1. Group observations by reporting period (YYYY-MM).
    2. If a month contains one or more IMPORTED records:
       - Drop all synthetic records for that month (never sum synthetic placeholders with real imports).
       - Aggregate multiple legitimate imported records by summing their values.
       - Composite source string from unique imported sources.
       - Mark monthly point data_status as 'IMPORTED'.
    3. If a month contains ONLY synthetic demonstration records:
       - Use the synthetic record(s).
       - Mark monthly point data_status as 'SYNTHETIC_DEMO'.
    4. Sort reconciled observations chronologically.
    5. Determine overall series provenance:
       - 'IMPORTED' if 100% of observations are imported.
       - 'SYNTHETIC_DEMO' if 100% of observations are synthetic.
       - 'HYBRID_BASELINE_PLUS_IMPORT' if series contains a mix of synthetic baseline and imported observations.
    6. Record explicit limitations regarding synthetic placeholders and lack of live government claims.
    """
    period_groups: dict[str, list] = {}
    for r in records:
        period_groups.setdefault(r.reporting_period, []).append(r)

    reconciled: list[TimeSeriesObservation] = []
    has_imported = False
    has_synthetic = False

    sorted_periods = sorted(period_groups.keys(), key=parse_period_to_ordinal)
    reconciled: list[TimeSeriesObservation] = []
    has_imported = False
    has_synthetic = False
    sanitized_negative = False

    for period in sorted_periods:
        group = period_groups[period]
        imported = [r for r in group if r.data_status == "IMPORTED"]
        synthetic = [r for r in group if r.data_status == "SYNTHETIC_DEMO"]

        if imported:
            has_imported = True
            raw_sum = sum(
                float(r.demand_value if target_metric == "DEMAND" else r.supply_value)
                for r in imported
            )
            if raw_sum < 0:
                sanitized_negative = True
                total_val = 0.0
            else:
                total_val = raw_sum

            sources = sorted({
                (r.source_system if target_metric == "DEMAND" else r.source_name)
                for r in imported
            })
            source_str = ", ".join(sources) if sources else "IMPORTED_BATCH"
            reconciled.append(
                TimeSeriesObservation(
                    period=period,
                    value=round(total_val, 2),
                    source=source_str,
                    data_status="IMPORTED",
                )
            )
        else:
            has_synthetic = True
            # For synthetic baseline records, deduplicate by taking representative value (prevent duplicate seed summation)
            synth_vals = [
                float(r.demand_value if target_metric == "DEMAND" else r.supply_value)
                for r in synthetic
            ]
            raw_val = synth_vals[0] if synth_vals else 0.0
            if raw_val < 0:
                sanitized_negative = True
                total_val = 0.0
            else:
                total_val = raw_val

            sources = sorted({
                (r.source_system if target_metric == "DEMAND" else r.source_name)
                for r in synthetic
            })
            source_str = ", ".join(sources) if sources else "SYNTHETIC_BASELINE"
            reconciled.append(
                TimeSeriesObservation(
                    period=period,
                    value=round(total_val, 2),
                    source=source_str,
                    data_status="SYNTHETIC_DEMO",
                )
            )

    limitations: list[str] = []
    if sanitized_negative:
        limitations.append(
            "DATA SANITIZATION: One or more negative observations were clamped to 0.0 "
            "as labour demand and supply cannot physically be negative."
        )

    # Check for discontinuous monthly reporting periods
    if len(sorted_periods) >= 2:
        ordinals = [parse_period_to_ordinal(p) for p in sorted_periods]
        missing_months = sum(ordinals[i] - ordinals[i - 1] - 1 for i in range(1, len(ordinals)) if ordinals[i] > ordinals[i - 1] + 1)
        if missing_months > 0:
            limitations.append(
                f"DISCONTINUOUS TIME SERIES: Historical data is missing {missing_months} calendar month(s) between "
                f"{sorted_periods[0]} and {sorted_periods[-1]}. Forecasting models assume regular monthly intervals."
            )

    if has_imported and has_synthetic:
        overall_status = "HYBRID_BASELINE_PLUS_IMPORT"
        limitations.append(
            "HYBRID PROVENANCE: Time series links synthetic demonstration baseline periods with reconciled imported employer postings. "
            "Synthetic placeholders were replaced wherever imported observations were available."
        )
    elif has_imported:
        overall_status = "IMPORTED"
        limitations.append(
            "IMPORTED PROVENANCE: Observations derived from imported employer postings. "
            "Does not represent official verified government statistical release."
        )
    elif has_synthetic:
        overall_status = "SYNTHETIC_DEMO"
        limitations.append(
            "SYNTHETIC DEMO: Historical series consists of calibrated synthetic demonstration data for Maharashtra pilot corridor."
        )
    else:
        overall_status = "INSUFFICIENT_DATA"

    return reconciled, overall_status, limitations


def generate_forecast_service(
    db: Session,
    request: GenerateForecastRequest,
) -> ForecastProjectionResponse:
    """Execute end-to-end forecasting pipeline with leakage prevention and holdout comparison."""
    nco_code = request.nco_code
    district_code = request.district_code
    target_metric = request.target_metric.upper()
    horizon = request.horizon_periods
    holdout_k = request.holdout_periods

    # 1. Fetch canonical occupation details if available
    occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == nco_code).first()
    canonical_title = occ.canonical_title if occ else None

    # 2. Retrieve raw observations from DB
    if target_metric == "DEMAND":
        records = (
            db.query(DemandObservation)
            .filter(
                DemandObservation.nco_code == nco_code,
                DemandObservation.district_code == district_code,
            )
            .all()
        )
    else:
        records = (
            db.query(QualifiedSupplyEstimate)
            .filter(
                QualifiedSupplyEstimate.nco_code == nco_code,
                QualifiedSupplyEstimate.district_code == district_code,
            )
            .all()
        )

    # Reconcile monthly series: enforce source precedence, multi-import aggregation, and hybrid provenance
    observations, overall_status, limitations = reconcile_time_series_observations(
        records, target_metric=target_metric
    )

    # 3. Check for sufficient historical series length
    N = len(observations)
    if N < 6:
        # Insufficient data condition
        scorecard = ModelEvaluationScorecard(
            evaluation_status="INSUFFICIENT_DATA",
            baseline_model_name="MOVING_AVERAGE_3M",
            candidate_model_name="HOLT_EXPONENTIAL_SMOOTHING",
            selected_model_name="NONE",
            train_start_period=observations[0].period if observations else None,
            train_end_period=observations[-1].period if observations else None,
            holdout_periods_count=holdout_k,
            total_historical_points=N,
            baseline_mae=None,
            candidate_mae=None,
            baseline_rmse=None,
            candidate_rmse=None,
            baseline_mape=None,
            candidate_mape=None,
            model_comparison_verdict=(
                f"Insufficient evidence for statistical forecasting: only {N} period(s) observed. "
                "A minimum of 6 contiguous historical reporting periods is required to support a 3-month "
                "training window and a 3-month chronological holdout evaluation."
            ),
        )
        limitations.append(
            f"Forecasting suppressed: {N} observation(s) available (minimum 6 required). "
            "Preventing fabricated projections based on inadequate history."
        )

        # Clear any existing stale forecast run for this series
        existing_run = (
            db.query(ForecastRun)
            .filter(
                ForecastRun.nco_code == nco_code,
                ForecastRun.district_code == district_code,
                ForecastRun.target_metric == target_metric,
            )
            .first()
        )
        if existing_run:
            existing_run.evaluation_status = "INSUFFICIENT_DATA"
            existing_run.selected_model_name = "NONE"
            existing_run.model_comparison_verdict = scorecard.model_comparison_verdict
            existing_run.total_historical_points = N
            existing_run.data_status = overall_status
            existing_run.limitations = "; ".join(limitations)
            db.query(ForecastPoint).filter(ForecastPoint.forecast_run_id == existing_run.id).delete()
            db.commit()

        return ForecastProjectionResponse(
            nco_code=nco_code,
            canonical_title=canonical_title,
            district_code=district_code,
            target_metric=target_metric,
            horizon_periods=horizon,
            historical_series=[
                HistoricalPointSchema(
                    period=o.period,
                    observed_value=o.value,
                    source_system=o.source,
                    data_status=o.data_status,
                )
                for o in observations
            ],
            forecast_points=[],
            evaluation=scorecard,
            data_status=overall_status,
            limitations=limitations,
        )

    # 4. Chronological holdout split (ZERO LEAKAGE)
    holdout_len = min(holdout_k, N - 3)  # Preserve at least 3 points for training
    train_obs = observations[:-holdout_len]
    test_obs = observations[-holdout_len:]

    train_values = [o.value for o in train_obs]
    test_values = [o.value for o in test_obs]

    # 5. Fit models on training set ONLY
    baseline_model = MovingAverageBaseline(window=3)
    baseline_model.fit(train_values)
    baseline_holdout_preds = baseline_model.predict(holdout_len)

    candidate_model = HoltExponentialSmoothing(alpha=0.35, beta=0.15)
    candidate_model.fit(train_values)
    candidate_holdout_preds = candidate_model.predict(holdout_len)

    # 6. Evaluate metrics strictly on holdout set
    b_mae, b_rmse, b_mape = compute_evaluation_metrics(test_values, baseline_holdout_preds)
    c_mae, c_rmse, c_mape = compute_evaluation_metrics(test_values, candidate_holdout_preds)

    # Model selection based on empirical holdout MAE
    if c_mae < b_mae:
        improvement = ((b_mae - c_mae) / b_mae) * 100.0 if b_mae > 0 else 0.0
        selected_name = "HOLT_EXPONENTIAL_SMOOTHING"
        verdict = (
            f"Candidate model ({selected_name}) outperformed 3M Moving Average baseline on {holdout_len}-month holdout "
            f"(MAE: {c_mae} vs {b_mae}, RMSE: {c_rmse} vs {b_rmse}, {improvement:.1f}% improvement). Selected for projection."
        )
    else:
        selected_name = "MOVING_AVERAGE_3M"
        verdict = (
            f"Baseline 3M Moving Average was retained: Candidate model did not demonstrate superior accuracy on holdout "
            f"(Baseline MAE: {b_mae} vs Candidate MAE: {c_mae}). Baseline selected to prevent overfitting."
        )

    # 7. Refit selected model on full historical dataset (all N observations)
    full_values = [o.value for o in observations]
    if selected_name == "HOLT_EXPONENTIAL_SMOOTHING":
        final_model = HoltExponentialSmoothing(alpha=0.35, beta=0.15)
        final_model.fit(full_values)
        raw_forecasts = final_model.predict(horizon)
        fitted = final_model.fitted_values
    else:
        final_base = MovingAverageBaseline(window=3)
        final_base.fit(full_values)
        raw_forecasts = final_base.predict(horizon)
        # 1-step-ahead in-sample fitted values using strictly prior observations (zero leakage)
        fitted = [full_values[0]]
        for t in range(1, len(full_values)):
            prior = full_values[max(0, t - 3) : t]
            fitted.append(sum(prior) / len(prior))

    # 8. Compute in-sample residual standard deviation for uncertainty intervals
    residuals = [act - fit for act, fit in zip(full_values, fitted)]
    # Degrees of freedom correction: N - 2 for two estimated parameters
    dof = max(1, len(residuals) - 2)
    var = sum(r**2 for r in residuals) / dof
    residual_std = math.sqrt(var)

    # 9. Build forward forecast points with mathematically grounded state-space prediction intervals
    last_period = observations[-1].period
    forecast_points: list[ForecastPointSchema] = []

    # Z-multiplier for ~80% nominal coverage under Gaussian error assumptions: 1.282
    z_mult = 1.282
    alpha = 0.35
    beta = 0.15

    for step, val in enumerate(raw_forecasts, start=1):
        step_period = add_months_to_period(last_period, step)
        if selected_name == "HOLT_EXPONENTIAL_SMOOTHING":
            # State-space variance expansion (Hyndman et al., Gardner 1985):
            # Var(e_{t+h}) = sigma^2 * [1 + sum_{j=1}^{h-1} (alpha + j * alpha * beta)^2]
            var_multiplier = 1.0 + sum((alpha + j * alpha * beta) ** 2 for j in range(1, step))
            se_step = residual_std * math.sqrt(var_multiplier)
        else:
            # Moving Average MA(3) error variance expansion
            se_step = residual_std * math.sqrt(1.0 + (step - 1) / 3.0)

        half_width = z_mult * se_step
        lower = max(0.0, round(val - half_width, 1))
        upper = round(val + half_width, 1)

        forecast_points.append(
            ForecastPointSchema(
                period=step_period,
                step_ahead=step,
                forecast_value=round(val, 1),
                lower_bound=lower,
                upper_bound=upper,
                confidence_level=0.80,
                is_projection=True,
                data_status=overall_status,
            )
        )

    limitations.append(
        "PREDICTION INTERVAL NOTICE: Bounds reflect approximate 80% nominal coverage under Gaussian error assumptions "
        "and analytical state-space variance expansion. Truncated at zero; does not account for structural economic shocks."
    )

    # 10. Persist or update ForecastRun in database (Idempotent upsert)
    limitations_text = "; ".join(limitations) if limitations else "Standard operational forecast."

    existing_run = (
        db.query(ForecastRun)
        .filter(
            ForecastRun.nco_code == nco_code,
            ForecastRun.district_code == district_code,
            ForecastRun.target_metric == target_metric,
        )
        .first()
    )

    if existing_run:
        db_run = existing_run
        db_run.horizon_periods = horizon
        db_run.baseline_model_name = "MOVING_AVERAGE_3M"
        db_run.candidate_model_name = "HOLT_EXPONENTIAL_SMOOTHING"
        db_run.selected_model_name = selected_name
        db_run.evaluation_status = "EVALUATED"
        db_run.train_start_period = train_obs[0].period
        db_run.train_end_period = train_obs[-1].period
        db_run.holdout_periods_count = holdout_len
        db_run.total_historical_points = N
        db_run.baseline_mae = b_mae
        db_run.candidate_mae = c_mae
        db_run.baseline_rmse = b_rmse
        db_run.candidate_rmse = c_rmse
        db_run.baseline_mape = b_mape
        db_run.candidate_mape = c_mape
        db_run.model_comparison_verdict = verdict
        db_run.data_status = overall_status
        db_run.limitations = limitations_text
        db_run.created_at = datetime.now(timezone.utc)
        # Clear previous forecast points
        db.query(ForecastPoint).filter(ForecastPoint.forecast_run_id == db_run.id).delete()
    else:
        run_id = f"FCST-{uuid.uuid4().hex[:12].upper()}"
        db_run = ForecastRun(
            run_id=run_id,
            nco_code=nco_code,
            district_code=district_code,
            target_metric=target_metric,
            frequency="MONTHLY",
            horizon_periods=horizon,
            baseline_model_name="MOVING_AVERAGE_3M",
            candidate_model_name="HOLT_EXPONENTIAL_SMOOTHING",
            selected_model_name=selected_name,
            evaluation_status="EVALUATED",
            train_start_period=train_obs[0].period,
            train_end_period=train_obs[-1].period,
            holdout_periods_count=holdout_len,
            total_historical_points=N,
            baseline_mae=b_mae,
            candidate_mae=c_mae,
            baseline_rmse=b_rmse,
            candidate_rmse=c_rmse,
            baseline_mape=b_mape,
            candidate_mape=c_mape,
            model_comparison_verdict=verdict,
            data_status=overall_status,
            limitations=limitations_text,
        )
        db.add(db_run)
        db.flush()

    for fp in forecast_points:
        db.add(
            ForecastPoint(
                forecast_run_id=db_run.id,
                period=fp.period,
                step_ahead=fp.step_ahead,
                forecast_value=fp.forecast_value,
                lower_bound=fp.lower_bound,
                upper_bound=fp.upper_bound,
                confidence_level=fp.confidence_level,
                is_projection=True,
                data_status=fp.data_status,
            )
        )
    db.commit()

    scorecard = ModelEvaluationScorecard(
        evaluation_status="EVALUATED",
        baseline_model_name="MOVING_AVERAGE_3M",
        candidate_model_name="HOLT_EXPONENTIAL_SMOOTHING",
        selected_model_name=selected_name,
        train_start_period=train_obs[0].period,
        train_end_period=train_obs[-1].period,
        holdout_periods_count=holdout_len,
        total_historical_points=N,
        baseline_mae=b_mae,
        candidate_mae=c_mae,
        baseline_rmse=b_rmse,
        candidate_rmse=c_rmse,
        baseline_mape=b_mape,
        candidate_mape=c_mape,
        model_comparison_verdict=verdict,
    )

    return ForecastProjectionResponse(
        nco_code=nco_code,
        canonical_title=canonical_title,
        district_code=district_code,
        target_metric=target_metric,
        horizon_periods=horizon,
        historical_series=[
            HistoricalPointSchema(
                period=o.period,
                observed_value=o.value,
                source_system=o.source,
                data_status=o.data_status,
            )
            for o in observations
        ],
        forecast_points=forecast_points,
        evaluation=scorecard,
        data_status=overall_status,
        limitations=limitations,
    )


def recompute_forecasts_for_occupations(
    db: Session,
    nco_codes: list[str] | None = None,
    district_codes: list[str] | None = None,
) -> int:
    """Automatically regenerate time series forecasts for occupations and districts.

    Triggered reactively when new demand observations are approved or updated.
    Guarantees idempotency and updates holdout evaluations and forward projections.
    """
    query = db.query(DemandObservation.nco_code, DemandObservation.district_code).distinct()
    if nco_codes:
        query = query.filter(DemandObservation.nco_code.in_(nco_codes))
    if district_codes:
        query = query.filter(DemandObservation.district_code.in_(district_codes))

    targets = query.all()
    count = 0
    for nco, district in targets:
        try:
            req = GenerateForecastRequest(
                nco_code=nco,
                district_code=district,
                target_metric="DEMAND",
                horizon_periods=3,
                holdout_periods=3,
            )
            generate_forecast_service(db, req)
            count += 1
        except Exception:
            continue

    return count


# Seed helper for demonstration history
DEMO_TIME_SERIES = [
    # 7421.0301 (Solar PV) in Pune (MH_PUN) - 18 months upward seasonal growth
    {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "observations": [
            ("2025-05", 410, 360),
            ("2025-06", 425, 365),
            ("2025-07", 390, 370),
            ("2025-08", 440, 375),
            ("2025-09", 480, 380),
            ("2025-10", 520, 390),
            ("2025-11", 540, 395),
            ("2025-12", 510, 400),
            ("2026-01", 550, 400),
            ("2026-02", 575, 405),
            ("2026-03", 600, 410),
            ("2026-04", 620, 410),
            ("2026-05", 610, 415),
            ("2026-06", 635, 415),
            ("2026-07", 615, 418),
            ("2026-08", 650, 420),
            ("2026-09", 665, 420),
            ("2026-10", 680, 420),
        ],
    },
    # 7421.0301 in Nashik (MH_NSK)
    {
        "nco_code": "7421.0301",
        "district_code": "MH_NSK",
        "observations": [
            ("2025-05", 210, 240),
            ("2025-06", 215, 245),
            ("2025-07", 205, 250),
            ("2025-08", 220, 250),
            ("2025-09", 235, 255),
            ("2025-10", 245, 260),
            ("2025-11", 250, 260),
            ("2025-12", 240, 265),
            ("2026-01", 260, 265),
            ("2026-02", 270, 270),
            ("2026-03", 275, 270),
            ("2026-04", 280, 272),
            ("2026-05", 275, 272),
            ("2026-06", 285, 274),
            ("2026-07", 280, 274),
            ("2026-08", 288, 275),
            ("2026-09", 285, 275),
            ("2026-10", 290, 275),
        ],
    },
    # 7233.0100 (Industrial Machinery) in Pune (MH_PUN)
    {
        "nco_code": "7233.0100",
        "district_code": "MH_PUN",
        "observations": [
            ("2025-05", 650, 480),
            ("2025-06", 670, 485),
            ("2025-07", 680, 485),
            ("2025-08", 700, 490),
            ("2025-09", 725, 495),
            ("2025-10", 740, 500),
            ("2025-11", 750, 500),
            ("2025-12", 730, 505),
            ("2026-01", 760, 505),
            ("2026-02", 780, 508),
            ("2026-03", 800, 510),
            ("2026-04", 810, 510),
            ("2026-05", 790, 510),
            ("2026-06", 820, 510),
            ("2026-07", 815, 510),
            ("2026-08", 830, 510),
            ("2026-09", 835, 510),
            ("2026-10", 840, 510),
        ],
    },
]


def seed_demo_time_series(db: Session) -> dict[str, int]:
    """Seed synthetic demonstration multi-month history for forecasting evaluation."""
    demand_count = 0
    supply_count = 0

    for series in DEMO_TIME_SERIES:
        nco_code = series["nco_code"]
        district = series["district_code"]

        for period, dem_val, sup_val in series["observations"]:
            # Check existing demand
            existing_d = (
                db.query(DemandObservation)
                .filter(
                    DemandObservation.nco_code == nco_code,
                    DemandObservation.district_code == district,
                    DemandObservation.reporting_period == period,
                )
                .first()
            )
            if not existing_d:
                db.add(
                    DemandObservation(
                        nco_code=nco_code,
                        district_code=district,
                        reporting_period=period,
                        demand_value=dem_val,
                        unit="OBSERVED_POSTINGS",
                        source_system="SYNTHETIC_NCS_ILLUSTRATIVE",
                        observation_method="SYNTHETIC_DEMO_SAMPLE",
                        data_status="SYNTHETIC_DEMO",
                        limitations="Synthetic demonstration monthly observation for time-series evaluation.",
                    )
                )
                demand_count += 1

            # Check existing supply
            existing_s = (
                db.query(QualifiedSupplyEstimate)
                .filter(
                    QualifiedSupplyEstimate.nco_code == nco_code,
                    QualifiedSupplyEstimate.district_code == district,
                    QualifiedSupplyEstimate.reporting_period == period,
                )
                .first()
            )
            if not existing_s:
                db.add(
                    QualifiedSupplyEstimate(
                        nco_code=nco_code,
                        district_code=district,
                        reporting_period=period,
                        supply_value=sup_val,
                        unit="QUALIFIED_WORKERS",
                        source_name="SYNTHETIC_NCVET_ILLUSTRATIVE",
                        estimation_method="SYNTHETIC_COHORT_SYNTHESIS",
                        data_status="SYNTHETIC_DEMO",
                        confidence_interval_low=int(sup_val * 0.92),
                        confidence_interval_high=int(sup_val * 1.08),
                        limitations="Synthetic demonstration monthly supply estimate for time-series evaluation.",
                    )
                )
                supply_count += 1

    db.commit()
    return {"demand_points_seeded": demand_count, "supply_points_seeded": supply_count}
