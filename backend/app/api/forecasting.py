"""Forecasting API routes.

Conforms to LMIS Master R&D Section 9 & 14:
- POST /api/forecasting/generate: Run transparent forecasting with chronological holdout.
- GET /api/forecasting/projections: Retrieve historical series and forward projections with confidence intervals.
- GET /api/forecasting/evaluations: List model evaluation scorecards comparing candidate vs baseline.
- POST /api/forecasting/seed-history: Seed synthetic demonstration time series.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.session import get_db
from backend.app.models.forecasting import ForecastRun, ForecastPoint
from backend.app.schemas.forecasting import (
    GenerateForecastRequest,
    ForecastProjectionResponse,
    ForecastEvaluationSummary,
)
from backend.app.services.forecasting import (
    generate_forecast_service,
    seed_demo_time_series,
)

router = APIRouter(prefix="/forecasting", tags=["Forecasting"])


@router.post(
    "/generate",
    response_model=ForecastProjectionResponse,
    summary="Generate statistical forecast with chronological holdout evaluation",
)
def generate_forecast(
    request: GenerateForecastRequest,
    db: Session = Depends(get_db),
):
    """Run model fitting, chronological holdout evaluation against 3M baseline, and forecast ahead."""
    res = generate_forecast_service(db, request)
    from backend.app.services.audit_service import record_audit_event
    record_audit_event(
        db=db,
        event_type="FORECAST_RUN",
        entity_type="OCCUPATION",
        entity_id=f"{request.nco_code}-{request.district_code}",
        action_summary=f"Forecast executed for {request.nco_code} ({request.district_code}): {res.evaluation.selected_model_name}",
        details={
            "nco_code": request.nco_code,
            "district_code": request.district_code,
            "target_metric": request.target_metric,
            "selected_model": res.evaluation.selected_model_name,
            "evaluation_status": res.evaluation.evaluation_status,
            "points_projected": len(res.forecast_points),
        },
    )
    return res


@router.get(
    "/projections",
    response_model=ForecastProjectionResponse,
    summary="Retrieve current projections, historical series, and evaluation scorecard",
)
def get_projections(
    nco_code: str = Query(..., description="NCO-2015 8-digit code (e.g. '7421.0301')"),
    district_code: str = Query(..., description="District code (e.g. 'MH_PUN')"),
    target_metric: str = Query("DEMAND", description="'DEMAND' or 'QUALIFIED_SUPPLY'"),
    horizon_periods: int = Query(3, ge=1, le=12, description="Forecast horizon in months"),
    db: Session = Depends(get_db),
):
    """Retrieve projections for an occupation and district. If none exists, runs a fresh forecast automatically."""
    req = GenerateForecastRequest(
        nco_code=nco_code,
        district_code=district_code,
        target_metric=target_metric,
        horizon_periods=horizon_periods,
    )
    return generate_forecast_service(db, req)


@router.get(
    "/evaluations",
    response_model=list[ForecastEvaluationSummary],
    summary="List model evaluation scorecards comparing Candidate vs Baseline",
)
def list_evaluations(
    district_code: str | None = Query(None, description="Filter by district"),
    nco_code: str | None = Query(None, description="Filter by occupation code"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve evaluation scorecards for auditing forecasting accuracy without data leakage."""
    q = db.query(ForecastRun)
    if district_code:
        q = q.filter(ForecastRun.district_code == district_code)
    if nco_code:
        q = q.filter(ForecastRun.nco_code == nco_code)

    runs = q.order_by(desc(ForecastRun.created_at)).limit(limit).all()

    return [
        ForecastEvaluationSummary(
            run_id=r.run_id,
            nco_code=r.nco_code,
            district_code=r.district_code,
            target_metric=r.target_metric,
            selected_model=r.selected_model_name,
            evaluation_status=r.evaluation_status,
            baseline_mae=r.baseline_mae,
            candidate_mae=r.candidate_mae,
            baseline_rmse=r.baseline_rmse,
            candidate_rmse=r.candidate_rmse,
            candidate_mape=r.candidate_mape,
            verdict=r.model_comparison_verdict,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in runs
    ]


@router.post(
    "/seed-history",
    summary="Seed synthetic demonstration time series observations for forecasting",
)
def seed_history(db: Session = Depends(get_db)):
    """Seed multi-month synthetic time series for Maharashtra pilot occupations to test forecasting models."""
    res = seed_demo_time_series(db)
    return {
        "status": "COMPLETED",
        "provenance": "SYNTHETIC_DEMO",
        "demand_points_seeded": res["demand_points_seeded"],
        "supply_points_seeded": res["supply_points_seeded"],
        "message": "Synthetic demonstration multi-month time series seeded successfully.",
    }
