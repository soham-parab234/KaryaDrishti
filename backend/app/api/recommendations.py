"""API endpoints for Policy Recommendations (Phase 10: Decision Intelligence)."""

import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.session import get_db
from backend.app.models.recommendations import PolicyRecommendation
from backend.app.schemas.recommendations import (
    PolicyRecommendationItem,
    RecommendationListResponse,
)
from backend.app.services.recommendations_service import generate_policy_recommendations

router = APIRouter(prefix="/recommendations", tags=["Decision Intelligence & Recommendations"])


@router.get(
    "",
    response_model=RecommendationListResponse,
    summary="List evidence-based policy and training recommendations",
)
def list_recommendations(
    nco_code: str | None = Query(None, description="Filter by NCO occupation code"),
    district_code: str | None = Query(None, description="Filter by district code"),
    recommendation_type: str | None = Query(None, description="Filter by archetype"),
    priority: str | None = Query(None, description="Filter by priority: HIGH, MEDIUM, LOW"),
    db: Session = Depends(get_db),
) -> RecommendationListResponse:
    """Retrieve active policy recommendations derived from gaps, forecasts, and capacity."""
    # If database has no recommendations yet, generate them dynamically
    if db.query(PolicyRecommendation).count() == 0:
        generate_policy_recommendations(db)

    query = db.query(PolicyRecommendation)
    if nco_code:
        query = query.filter(PolicyRecommendation.nco_code == nco_code)
    if district_code:
        query = query.filter(PolicyRecommendation.district_code == district_code)
    if recommendation_type:
        query = query.filter(PolicyRecommendation.recommendation_type == recommendation_type)
    if priority:
        query = query.filter(PolicyRecommendation.priority == priority)

    records = query.order_by(
        desc(PolicyRecommendation.priority == "HIGH"),
        PolicyRecommendation.nco_code,
    ).all()

    items = [
        PolicyRecommendationItem(
            recommendation_id=r.recommendation_id,
            nco_code=r.nco_code,
            canonical_title=r.canonical_title,
            district_code=r.district_code,
            reporting_period=r.reporting_period,
            recommendation_type=r.recommendation_type,
            action_title=r.action_title,
            priority=r.priority,
            rationale=r.rationale,
            evidence_sources=json.loads(r.evidence_sources) if isinstance(r.evidence_sources, str) else r.evidence_sources,
            proposed_seat_adjustment=r.proposed_seat_adjustment,
            target_horizon_months=r.target_horizon_months,
            expected_impact_summary=r.expected_impact_summary,
            feasibility_score=r.feasibility_score,
            data_status=r.data_status,
            limitations=json.loads(r.limitations) if isinstance(r.limitations, str) else r.limitations,
            created_at=r.created_at,
        )
        for r in records
    ]

    return RecommendationListResponse(
        total_recommendations=len(items),
        expansion_count=sum(1 for i in items if i.recommendation_type == "TRAINING_CAPACITY_EXPANSION"),
        curriculum_pivot_count=sum(1 for i in items if i.recommendation_type == "CURRICULUM_MODERNIZATION_OR_PIVOT"),
        apprenticeship_count=sum(1 for i in items if i.recommendation_type == "APPRENTICESHIP_INDUSTRY_TIE_UP"),
        data_audit_count=sum(1 for i in items if i.recommendation_type == "DATA_COLLECTION_AUDIT"),
        items=items,
    )


@router.post(
    "/evaluate",
    response_model=RecommendationListResponse,
    summary="Evaluate current labour market evidence and regenerate recommendations",
)
def evaluate_recommendations(
    db: Session = Depends(get_db),
) -> RecommendationListResponse:
    """Run full rule-based decision intelligence engine and refresh recommendations."""
    return generate_policy_recommendations(db)
