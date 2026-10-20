"""Pydantic schemas for forecasting and model holdout evaluation.

Conforms to LMIS Master R&D Section 9:
- Strictly documents model comparison against baseline.
- Keeps historical observations separate from future projections.
- Discloses evaluation status (EVALUATED, NOT_EVALUATED, INSUFFICIENT_DATA).
- Conveys uncertainty intervals and data limitations clearly.
"""

from pydantic import BaseModel, Field


class HistoricalPointSchema(BaseModel):
    """Historical observation used as training or evaluation input."""

    period: str = Field(..., description="Reporting period (e.g. '2026-05')")
    observed_value: float = Field(..., description="Empirically observed or synthetic demonstration value")
    source_system: str = Field(..., description="Source system or feed name")
    data_status: str = Field(..., description="Data status (e.g. 'SYNTHETIC_DEMO')")


class ForecastPointSchema(BaseModel):
    """Point forecast and uncertainty interval for a future period."""

    period: str = Field(..., description="Projected period (e.g. '2026-11')")
    step_ahead: int = Field(..., description="Forecast step ahead (1, 2, ...)")
    forecast_value: float = Field(..., description="Point prediction")
    lower_bound: float | None = Field(None, description="Lower prediction bound")
    upper_bound: float | None = Field(None, description="Upper prediction bound")
    confidence_level: float | None = Field(0.80, description="Nominal coverage probability (e.g. 0.80 for 80% nominal interval)")
    is_projection: bool = Field(True, description="True for forward predictions; False for holdout fitted values")
    data_status: str = Field("SYNTHETIC_DEMO", description="'SYNTHETIC_DEMO', 'HYBRID_BASELINE_PLUS_IMPORT', or 'IMPORTED'")


class ModelEvaluationScorecard(BaseModel):
    """Transparent comparison between candidate model and baseline model."""

    evaluation_status: str = Field(..., description="'EVALUATED', 'NOT_EVALUATED', or 'INSUFFICIENT_DATA'")
    baseline_model_name: str = Field("MOVING_AVERAGE_3M", description="Baseline model identifier")
    candidate_model_name: str = Field("HOLT_EXPONENTIAL_SMOOTHING", description="Candidate model identifier")
    selected_model_name: str = Field(..., description="Model selected for final projections")
    train_start_period: str | None = Field(None, description="First period in training set")
    train_end_period: str | None = Field(None, description="Last period in training set")
    holdout_periods_count: int = Field(3, description="Number of chronological holdout periods")
    total_historical_points: int = Field(..., description="Total historical observation points available")
    baseline_mae: float | None = Field(None, description="Baseline Mean Absolute Error on holdout")
    candidate_mae: float | None = Field(None, description="Candidate Mean Absolute Error on holdout")
    baseline_rmse: float | None = Field(None, description="Baseline Root Mean Squared Error on holdout")
    candidate_rmse: float | None = Field(None, description="Candidate Root Mean Squared Error on holdout")
    baseline_mape: float | None = Field(None, description="Baseline Mean Absolute Percentage Error (%) on holdout")
    candidate_mape: float | None = Field(None, description="Candidate Mean Absolute Percentage Error (%) on holdout")
    model_comparison_verdict: str = Field(..., description="Comparative evaluation summary explaining model choice")
    leakage_prevention_notice: str = Field(
        "Strict chronological split: Models were trained solely on historical periods prior to holdout window. Zero future information leakage.",
        description="Assurance of chronological holdout integrity",
    )


class ForecastProjectionResponse(BaseModel):
    """Complete forecast package containing history, projections, evaluation, and provenance."""

    nco_code: str
    canonical_title: str | None = None
    district_code: str
    target_metric: str = Field("DEMAND", description="'DEMAND' or 'QUALIFIED_SUPPLY'")
    horizon_periods: int
    historical_series: list[HistoricalPointSchema] = Field(default_factory=list)
    forecast_points: list[ForecastPointSchema] = Field(default_factory=list)
    evaluation: ModelEvaluationScorecard
    data_status: str = Field("SYNTHETIC_DEMO", description="'SYNTHETIC_DEMO', 'HYBRID_BASELINE_PLUS_IMPORT', or 'IMPORTED'")
    limitations: list[str] = Field(default_factory=list)


class GenerateForecastRequest(BaseModel):
    """Request payload to generate or update an occupation forecast."""

    nco_code: str = Field(..., description="NCO-2015 8-digit occupation code")
    district_code: str = Field(..., description="District identifier (e.g. 'MH_PUN')")
    target_metric: str = Field("DEMAND", description="'DEMAND' or 'QUALIFIED_SUPPLY'")
    horizon_periods: int = Field(3, ge=1, le=12, description="Forecast horizon in months (1-12)")
    holdout_periods: int = Field(3, ge=1, le=6, description="Evaluation holdout window in months (1-6)")
    confidence_level: float = Field(0.80, ge=0.50, le=0.99, description="Confidence interval coverage (0.50 to 0.99)")


class ForecastEvaluationSummary(BaseModel):
    """Summary item for listing forecast evaluations across occupations."""

    run_id: str
    nco_code: str
    district_code: str
    target_metric: str
    selected_model: str
    evaluation_status: str
    baseline_mae: float | None
    candidate_mae: float | None
    baseline_rmse: float | None
    candidate_rmse: float | None
    candidate_mape: float | None
    verdict: str
    created_at: str
