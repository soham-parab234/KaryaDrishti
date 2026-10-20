"""Policy and Training Recommendation Database Models.

Represents practical, explainable training and workforce policy recommendations
derived from observed demand-supply gaps, Holt forecasting projections,
and institutional training capacities.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Index
from backend.app.db.base import Base


class PolicyRecommendation(Base):
    """Stores derived evidence-based policy recommendations for occupations and districts."""

    __tablename__ = "policy_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(String(100), unique=True, index=True, nullable=False)
    nco_code = Column(String(20), index=True, nullable=False)
    canonical_title = Column(String(200), nullable=True)
    district_code = Column(String(20), index=True, nullable=False)
    reporting_period = Column(String(10), nullable=False)  # YYYY-MM
    
    # Archetype: TRAINING_CAPACITY_EXPANSION, CURRICULUM_MODERNIZATION_OR_PIVOT,
    # APPRENTICESHIP_INDUSTRY_TIE_UP, DATA_COLLECTION_AUDIT
    recommendation_type = Column(String(50), nullable=False)
    action_title = Column(String(250), nullable=False)
    priority = Column(String(20), nullable=False, default="MEDIUM")  # HIGH, MEDIUM, LOW
    
    # Full mathematical & empirical rationale
    rationale = Column(Text, nullable=False)
    
    # JSON or serialized details of evidence sources (gap, forecast trend, seat utilization)
    evidence_sources = Column(Text, nullable=False)
    
    # Proposed training seats adjustment (positive for expansion, negative/zero for realignment)
    proposed_seat_adjustment = Column(Integer, nullable=False, default=0)
    target_horizon_months = Column(Integer, nullable=False, default=12)
    expected_impact_summary = Column(Text, nullable=False)
    feasibility_score = Column(Float, nullable=False, default=0.75)
    
    # Provenance and status: CONFIRMED_OBSERVATION, PROJECTION_BASED, DATA_DEFICIT_ADVISORY, SYNTHETIC_DEMO
    data_status = Column(String(50), nullable=False, default="PROJECTION_BASED")
    limitations = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_policy_rec_nco_district", "nco_code", "district_code", "reporting_period"),
    )
