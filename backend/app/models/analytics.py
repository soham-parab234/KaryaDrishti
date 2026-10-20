"""SQLAlchemy models for demand observations, qualified supply estimates, and training capacity.

Conforms strictly to LMIS Master R&D Section 8:
- Observed demand signals are separated from qualified supply estimates.
- Sanctioned training seats represent capacity, NOT available supply.
- Every observation records geography, period, source, unit, method, and provenance status.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class DemandObservation(Base):
    """Documented employer hiring signal observation for an occupation, geography, and period."""

    __tablename__ = "demand_observations"
    __table_args__ = (
        UniqueConstraint("nco_code", "district_code", "reporting_period", "source_system", name="uq_demand_obs"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nco_code: Mapped[str] = mapped_column(String(20), ForeignKey("nco_occupations.nco_code"), nullable=False, index=True)
    district_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reporting_period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # Format: YYYY-MM
    demand_value: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="OBSERVED_POSTINGS", nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    observation_method: Mapped[str] = mapped_column(String(80), nullable=False)
    data_status: Mapped[str] = mapped_column(String(50), default="PILOT_BASELINE", nullable=False)
    unresolved_postings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_postings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    occupation: Mapped["NcoOccupation"] = relationship("NcoOccupation")

class QualifiedSupplyEstimate(Base):
    """Estimated pool of workers plausibly qualified for an occupation, geography, and period."""

    __tablename__ = "qualified_supply_estimates"
    __table_args__ = (
        UniqueConstraint("nco_code", "district_code", "reporting_period", "source_name", name="uq_supply_est"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nco_code: Mapped[str] = mapped_column(String(20), ForeignKey("nco_occupations.nco_code"), nullable=False, index=True)
    district_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reporting_period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # Format: YYYY-MM
    supply_value: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="QUALIFIED_WORKERS", nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    estimation_method: Mapped[str] = mapped_column(String(80), nullable=False)
    data_status: Mapped[str] = mapped_column(String(50), default="PILOT_BASELINE", nullable=False)
    confidence_interval_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_interval_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    occupation: Mapped["NcoOccupation"] = relationship("NcoOccupation")

class TrainingCapacityOutcome(Base):
    """Institutional training capacity and graduate outcomes (strictly separated from active supply)."""

    __tablename__ = "training_capacity_outcomes"
    __table_args__ = (
        UniqueConstraint("nco_code", "district_code", "reporting_period", "source_system", name="uq_training_cap"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nco_code: Mapped[str] = mapped_column(String(20), ForeignKey("nco_occupations.nco_code"), nullable=False, index=True)
    district_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reporting_period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    sanctioned_seats: Mapped[int] = mapped_column(Integer, nullable=False)  # Capacity, NOT supply
    enrolled_students: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_students: Mapped[int | None] = mapped_column(Integer, nullable=True)
    placed_students: Mapped[int | None] = mapped_column(Integer, nullable=True)
    placement_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)
    data_status: Mapped[str] = mapped_column(String(50), default="PILOT_BASELINE", nullable=False)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    occupation: Mapped["NcoOccupation"] = relationship("NcoOccupation")
