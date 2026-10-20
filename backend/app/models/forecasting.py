"""Forecasting database models.

Conforms to LMIS Master R&D Section 9:
- Stores forecast runs, model versions, horizons, training windows, and evaluation metrics.
- Separates observed historical values from forward-looking projections.
- Persists uncertainty bounds (upper/lower bounds) with explicit confidence levels.
- Records data provenance and explicit limitations.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ForecastRun(Base):
    """Execution record of a time series forecast and holdout evaluation."""

    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nco_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    district_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    target_metric: Mapped[str] = mapped_column(String(50), default="DEMAND", nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="MONTHLY", nullable=False)
    horizon_periods: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Model metadata
    baseline_model_name: Mapped[str] = mapped_column(String(100), default="MOVING_AVERAGE_3M", nullable=False)
    candidate_model_name: Mapped[str] = mapped_column(String(100), default="HOLT_EXPONENTIAL_SMOOTHING", nullable=False)
    selected_model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Evaluation and holdout window
    evaluation_status: Mapped[str] = mapped_column(
        String(50), default="EVALUATED", nullable=False
    )  # EVALUATED, NOT_EVALUATED, INSUFFICIENT_DATA
    train_start_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    train_end_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    holdout_periods_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    total_historical_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Holdout validation metrics
    baseline_mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_mape: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Comparison verdict
    model_comparison_verdict: Mapped[str] = mapped_column(Text, nullable=False)

    # Provenance and caveats
    data_status: Mapped[str] = mapped_column(String(50), default="SYNTHETIC_DEMO", nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Points relationship
    points: Mapped[list["ForecastPoint"]] = relationship(
        "ForecastPoint",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ForecastPoint.step_ahead",
    )

    __table_args__ = (
        Index("ix_forecast_query", "nco_code", "district_code", "target_metric"),
    )


class ForecastPoint(Base):
    """Individual projected or historical validation data point."""

    __tablename__ = "forecast_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("forecast_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2026-11"
    step_ahead: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3...
    forecast_value: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[float | None] = mapped_column(Float, default=0.80, nullable=True)
    is_projection: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_status: Mapped[str] = mapped_column(String(50), default="SYNTHETIC_DEMO", nullable=False)

    run: Mapped["ForecastRun"] = relationship("ForecastRun", back_populates="points")
