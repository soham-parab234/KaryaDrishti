"""Demand–Supply Analytics and Labour Market Gap Engine API Endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.db.session import get_db
from backend.app.models.occupation import NcoOccupation
from backend.app.models.analytics import (
    DemandObservation,
    QualifiedSupplyEstimate,
    TrainingCapacityOutcome,
)
from backend.app.schemas.analytics import (
    DemandObservationCreate,
    DemandObservationItem,
    QualifiedSupplyEstimateCreate,
    QualifiedSupplyEstimateItem,
    TrainingCapacityCreate,
    TrainingCapacityItem,
    GapIndicatorSummary,
    GapDetailAuditResponse,
    DemandAggregationResponse,
    PipelineRecomputeResponse,
)
from backend.app.services.gap_calculator import (
    assess_evidence_compatibility,
    calculate_absolute_gap,
    calculate_gap_rate,
)
from backend.app.services.analytics_service import (
    aggregate_demand_from_postings,
    seed_pilot_baseline_analytics,
)

router = APIRouter(prefix="/analytics", tags=["Demand-Supply Analytics & Gaps"])

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# --- 1. Demand Endpoints ---

@router.post(
    "/demand",
    response_model=DemandObservationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record an employer demand observation",
)
def create_demand_observation(
    payload: DemandObservationCreate,
    db: Session = Depends(get_db),
) -> DemandObservationItem:
    """Record an observed employer hiring signal for an occupation, geography, and period."""
    occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == payload.nco_code).first()
    if not occ:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NCO code '{payload.nco_code}' not found in reference taxonomy.",
        )

    existing = (
        db.query(DemandObservation)
        .filter(
            DemandObservation.nco_code == payload.nco_code,
            DemandObservation.district_code == payload.district_code,
            DemandObservation.reporting_period == payload.reporting_period,
            DemandObservation.source_system == payload.source_system,
        )
        .first()
    )

    if existing:
        existing.demand_value = payload.demand_value
        existing.unit = payload.unit
        existing.observation_method = payload.observation_method
        existing.data_status = payload.data_status
        existing.limitations = payload.limitations
        existing.updated_at = utc_now()
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        new_obs = DemandObservation(
            nco_code=payload.nco_code,
            district_code=payload.district_code,
            reporting_period=payload.reporting_period,
            demand_value=payload.demand_value,
            unit=payload.unit,
            source_system=payload.source_system,
            observation_method=payload.observation_method,
            data_status=payload.data_status,
            limitations=payload.limitations,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(new_obs)
        db.commit()
        db.refresh(new_obs)
        target = new_obs

    return DemandObservationItem(
        id=target.id,
        nco_code=target.nco_code,
        canonical_title=occ.canonical_title,
        district_code=target.district_code,
        reporting_period=target.reporting_period,
        demand_value=target.demand_value,
        unit=target.unit,
        source_system=target.source_system,
        observation_method=target.observation_method,
        data_status=target.data_status,
        unresolved_postings_count=target.unresolved_postings_count,
        rejected_postings_count=target.rejected_postings_count,
        limitations=target.limitations,
        created_at=target.created_at.isoformat(),
    )

@router.post(
    "/demand/aggregate-from-postings",
    response_model=DemandAggregationResponse,
    summary="Aggregate confirmed demand from approved title mapping reviews",
)
def aggregate_postings(
    batch_id: str | None = Query(None, description="Optional batch ID to aggregate; aggregates all batches if omitted"),
    db: Session = Depends(get_db),
) -> DemandAggregationResponse:
    """Derive demand observations exclusively from approved job postings. Excludes unapproved/rejected records."""
    return aggregate_demand_from_postings(db, batch_id=batch_id)

@router.post(
    "/recompute-pipeline",
    response_model=PipelineRecomputeResponse,
    summary="Recompute demand from approved postings, recalculate gaps, and refresh early-warning alerts",
)
def recompute_intelligence_pipeline(
    batch_id: str | None = Query(None, description="Optional batch ID to aggregate; aggregates all batches if omitted"),
    db: Session = Depends(get_db),
) -> PipelineRecomputeResponse:
    """End-to-end intelligence pipeline execution:
    1. Aggregates all approved job postings into DemandObservation records.
    2. Excludes unapproved/unresolved postings and tracks them in limitations.
    3. Re-evaluates rule-based early-warning alerts across all occupations and districts.
    4. Returns comprehensive execution metrics.
    """
    from backend.app.services.forecasting import recompute_forecasts_for_occupations
    from backend.app.services.alerts_service import evaluate_and_generate_alerts
    from backend.app.services.recommendations_service import generate_policy_recommendations

    agg_res = aggregate_demand_from_postings(db, batch_id=batch_id)
    fcst_count = recompute_forecasts_for_occupations(db)
    alert_res = evaluate_and_generate_alerts(db)
    rec_res = generate_policy_recommendations(db)

    from backend.app.services.audit_service import record_audit_event
    record_audit_event(
        db=db,
        event_type="PIPELINE_RECOMPUTE",
        entity_type="PIPELINE",
        entity_id=batch_id or "ALL_BATCHES",
        action_summary=(
            f"Pipeline recompute: Aggregated {agg_res.total_approved_postings_aggregated} vacancies, "
            f"{fcst_count} forecasts, {alert_res.total_alerts_evaluated} alerts, {rec_res.total_recommendations} recommendations."
        ),
        actor="SYSTEM_PIPELINE",
        details={
            "approved_vacancies": agg_res.total_approved_postings_aggregated,
            "unresolved_excluded": agg_res.unresolved_postings_excluded,
            "observations_updated": agg_res.observations_created_or_updated,
            "forecasts_recomputed": fcst_count,
            "alerts_evaluated": alert_res.total_alerts_evaluated,
            "recommendations_generated": rec_res.total_recommendations,
        },
    )

    return PipelineRecomputeResponse(
        total_approved_postings_aggregated=agg_res.total_approved_postings_aggregated,
        unresolved_postings_excluded=agg_res.unresolved_postings_excluded,
        rejected_postings_excluded=agg_res.rejected_postings_excluded,
        observations_created_or_updated=agg_res.observations_created_or_updated,
        forecasts_recomputed=fcst_count,
        recommendations_generated=rec_res.total_recommendations,
        alerts_evaluated=alert_res.total_alerts_evaluated,
        critical_alerts_count=alert_res.critical_count,
        warning_alerts_count=alert_res.warning_count,
        info_alerts_count=alert_res.info_count,
        message=(
            f"Pipeline successfully recomputed: Aggregated {agg_res.total_approved_postings_aggregated} confirmed vacancy(ies) "
            f"across {agg_res.observations_created_or_updated} demand observation(s). "
            f"Excluded {agg_res.unresolved_postings_excluded} unapproved posting(s). "
            f"Recomputed {fcst_count} time-series forecast(s). "
            f"Refreshed {alert_res.total_alerts_evaluated} early-warning alerts ({alert_res.critical_count} critical, {alert_res.warning_count} warning). "
            f"Generated {rec_res.total_recommendations} actionable policy recommendation(s)."
        ),
    )

@router.get(
    "/demand",
    response_model=list[DemandObservationItem],
    summary="List demand observations with filters",
)
def list_demand_observations(
    nco_code: str | None = Query(None),
    district_code: str | None = Query(None),
    reporting_period: str | None = Query(None),
    data_status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[DemandObservationItem]:
    """Retrieve recorded demand observations."""
    query = db.query(DemandObservation)
    if nco_code:
        query = query.filter(DemandObservation.nco_code == nco_code)
    if district_code:
        query = query.filter(DemandObservation.district_code == district_code)
    if reporting_period:
        query = query.filter(DemandObservation.reporting_period == reporting_period)
    if data_status:
        query = query.filter(DemandObservation.data_status == data_status)

    items = query.order_by(DemandObservation.reporting_period.desc()).offset(offset).limit(limit).all()

    return [
        DemandObservationItem(
            id=d.id,
            nco_code=d.nco_code,
            canonical_title=d.occupation.canonical_title if d.occupation else None,
            district_code=d.district_code,
            reporting_period=d.reporting_period,
            demand_value=d.demand_value,
            unit=d.unit,
            source_system=d.source_system,
            observation_method=d.observation_method,
            data_status=d.data_status,
            unresolved_postings_count=d.unresolved_postings_count,
            rejected_postings_count=d.rejected_postings_count,
            limitations=d.limitations,
            created_at=d.created_at.isoformat(),
        )
        for d in items
    ]

# --- 2. Qualified Supply Endpoints ---

@router.post(
    "/supply",
    response_model=QualifiedSupplyEstimateItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record a qualified supply estimate",
)
def create_supply_estimate(
    payload: QualifiedSupplyEstimateCreate,
    db: Session = Depends(get_db),
) -> QualifiedSupplyEstimateItem:
    """Record an estimated pool of qualified workers for an occupation, geography, and period."""
    occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == payload.nco_code).first()
    if not occ:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NCO code '{payload.nco_code}' not found in reference taxonomy.",
        )

    existing = (
        db.query(QualifiedSupplyEstimate)
        .filter(
            QualifiedSupplyEstimate.nco_code == payload.nco_code,
            QualifiedSupplyEstimate.district_code == payload.district_code,
            QualifiedSupplyEstimate.reporting_period == payload.reporting_period,
            QualifiedSupplyEstimate.source_name == payload.source_name,
        )
        .first()
    )

    if existing:
        existing.supply_value = payload.supply_value
        existing.unit = payload.unit
        existing.estimation_method = payload.estimation_method
        existing.data_status = payload.data_status
        existing.confidence_interval_low = payload.confidence_interval_low
        existing.confidence_interval_high = payload.confidence_interval_high
        existing.limitations = payload.limitations
        existing.updated_at = utc_now()
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        new_sup = QualifiedSupplyEstimate(
            nco_code=payload.nco_code,
            district_code=payload.district_code,
            reporting_period=payload.reporting_period,
            supply_value=payload.supply_value,
            unit=payload.unit,
            source_name=payload.source_name,
            estimation_method=payload.estimation_method,
            data_status=payload.data_status,
            confidence_interval_low=payload.confidence_interval_low,
            confidence_interval_high=payload.confidence_interval_high,
            limitations=payload.limitations,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(new_sup)
        db.commit()
        db.refresh(new_sup)
        target = new_sup

    return QualifiedSupplyEstimateItem(
        id=target.id,
        nco_code=target.nco_code,
        canonical_title=occ.canonical_title,
        district_code=target.district_code,
        reporting_period=target.reporting_period,
        supply_value=target.supply_value,
        unit=target.unit,
        source_name=target.source_name,
        estimation_method=target.estimation_method,
        data_status=target.data_status,
        confidence_interval_low=target.confidence_interval_low,
        confidence_interval_high=target.confidence_interval_high,
        limitations=target.limitations,
        created_at=target.created_at.isoformat(),
    )

@router.get(
    "/supply",
    response_model=list[QualifiedSupplyEstimateItem],
    summary="List qualified supply estimates with filters",
)
def list_supply_estimates(
    nco_code: str | None = Query(None),
    district_code: str | None = Query(None),
    reporting_period: str | None = Query(None),
    data_status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[QualifiedSupplyEstimateItem]:
    """Retrieve recorded qualified supply estimates."""
    query = db.query(QualifiedSupplyEstimate)
    if nco_code:
        query = query.filter(QualifiedSupplyEstimate.nco_code == nco_code)
    if district_code:
        query = query.filter(QualifiedSupplyEstimate.district_code == district_code)
    if reporting_period:
        query = query.filter(QualifiedSupplyEstimate.reporting_period == reporting_period)
    if data_status:
        query = query.filter(QualifiedSupplyEstimate.data_status == data_status)

    items = query.order_by(QualifiedSupplyEstimate.reporting_period.desc()).offset(offset).limit(limit).all()

    return [
        QualifiedSupplyEstimateItem(
            id=s.id,
            nco_code=s.nco_code,
            canonical_title=s.occupation.canonical_title if s.occupation else None,
            district_code=s.district_code,
            reporting_period=s.reporting_period,
            supply_value=s.supply_value,
            unit=s.unit,
            source_name=s.source_name,
            estimation_method=s.estimation_method,
            data_status=s.data_status,
            confidence_interval_low=s.confidence_interval_low,
            confidence_interval_high=s.confidence_interval_high,
            limitations=s.limitations,
            created_at=s.created_at.isoformat(),
        )
        for s in items
    ]

# --- 3. Training Capacity Endpoints (Separated from Supply) ---

@router.post(
    "/training-capacity",
    response_model=TrainingCapacityItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record institutional training capacity and outcomes",
)
def create_training_capacity(
    payload: TrainingCapacityCreate,
    db: Session = Depends(get_db),
) -> TrainingCapacityItem:
    """Record sanctioned training seats and graduate outcomes. Strictly separated from available supply."""
    occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == payload.nco_code).first()
    if not occ:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NCO code '{payload.nco_code}' not found in reference taxonomy.",
        )

    cap = TrainingCapacityOutcome(
        nco_code=payload.nco_code,
        district_code=payload.district_code,
        reporting_period=payload.reporting_period,
        sanctioned_seats=payload.sanctioned_seats,
        enrolled_students=payload.enrolled_students,
        completed_students=payload.completed_students,
        placed_students=payload.placed_students,
        placement_rate_pct=payload.placement_rate_pct,
        source_system=payload.source_system,
        data_status=payload.data_status,
        limitations=payload.limitations,
        created_at=utc_now(),
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)

    return TrainingCapacityItem(
        id=cap.id,
        nco_code=cap.nco_code,
        canonical_title=occ.canonical_title,
        district_code=cap.district_code,
        reporting_period=cap.reporting_period,
        sanctioned_seats=cap.sanctioned_seats,
        enrolled_students=cap.enrolled_students,
        completed_students=cap.completed_students,
        placed_students=cap.placed_students,
        placement_rate_pct=cap.placement_rate_pct,
        source_system=cap.source_system,
        data_status=cap.data_status,
        limitations=cap.limitations,
        created_at=cap.created_at.isoformat(),
    )

# --- 4. Gap Indicators & Detail Audit ---

@router.get(
    "/gaps",
    response_model=list[GapIndicatorSummary],
    summary="Query demand-supply gap indicators with full evidence status",
)
def list_gap_indicators(
    district_code: str | None = Query(None, description="Filter by district code (e.g. MH_PUN, MH_NSK)"),
    reporting_period: str | None = Query(None, description="Filter by reporting period (YYYY-MM)"),
    nco_code: str | None = Query(None, description="Filter by NCO code"),
    data_status: str | None = Query(None, description="Filter by data provenance"),
    db: Session = Depends(get_db),
) -> list[GapIndicatorSummary]:
    """Retrieve demand, supply, and gap indicators conforming to Master R&D Section 8 formulas."""
    # Find all unique combinations of (nco_code, district_code, reporting_period) from demand and supply
    demand_keys = (
        db.query(DemandObservation.nco_code, DemandObservation.district_code, DemandObservation.reporting_period)
    )
    supply_keys = (
        db.query(QualifiedSupplyEstimate.nco_code, QualifiedSupplyEstimate.district_code, QualifiedSupplyEstimate.reporting_period)
    )

    if district_code:
        demand_keys = demand_keys.filter(DemandObservation.district_code == district_code)
        supply_keys = supply_keys.filter(QualifiedSupplyEstimate.district_code == district_code)
    if reporting_period:
        demand_keys = demand_keys.filter(DemandObservation.reporting_period == reporting_period)
        supply_keys = supply_keys.filter(QualifiedSupplyEstimate.reporting_period == reporting_period)
    if nco_code:
        demand_keys = demand_keys.filter(DemandObservation.nco_code == nco_code)
        supply_keys = supply_keys.filter(QualifiedSupplyEstimate.nco_code == nco_code)

    all_keys = set(demand_keys.all()).union(set(supply_keys.all()))

    results: list[GapIndicatorSummary] = []

    for code, dist, period in sorted(list(all_keys)):
        occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == code).first()
        canonical_title = occ.canonical_title if occ else code

        demand = (
            db.query(DemandObservation)
            .filter(
                DemandObservation.nco_code == code,
                DemandObservation.district_code == dist,
                DemandObservation.reporting_period == period,
            )
            .first()
        )

        supply = (
            db.query(QualifiedSupplyEstimate)
            .filter(
                QualifiedSupplyEstimate.nco_code == code,
                QualifiedSupplyEstimate.district_code == dist,
                QualifiedSupplyEstimate.reporting_period == period,
            )
            .first()
        )

        demand_val = demand.demand_value if demand else None
        demand_status = demand.data_status if demand else None
        supply_val = supply.supply_value if supply else None
        supply_status = supply.data_status if supply else None

        assessment = assess_evidence_compatibility(
            demand_val=demand_val,
            demand_period=demand.reporting_period if demand else None,
            demand_district=demand.district_code if demand else None,
            demand_status=demand_status,
            supply_val=supply_val,
            supply_period=supply.reporting_period if supply else None,
            supply_district=supply.district_code if supply else None,
            supply_status=supply_status,
            unresolved_postings=demand.unresolved_postings_count if demand else 0,
            rejected_postings=demand.rejected_postings_count if demand else 0,
        )

        if data_status and assessment.combined_data_status != data_status:
            continue

        if assessment.evidence_status == "CALCULATED" and demand_val is not None and supply_val is not None:
            abs_gap = calculate_absolute_gap(demand_val, supply_val)
            gap_rate, _ = calculate_gap_rate(demand_val, supply_val)
        else:
            abs_gap = None
            gap_rate = None

        results.append(
            GapIndicatorSummary(
                nco_code=code,
                canonical_title=canonical_title,
                district_code=dist,
                reporting_period=period,
                demand_value=demand_val,
                qualified_supply_value=supply_val,
                absolute_gap=abs_gap,
                gap_rate_pct=gap_rate,
                evidence_status=assessment.evidence_status,
                data_status=assessment.combined_data_status,
                is_suitable_for_planning=assessment.is_suitable_for_planning,
            )
        )

    return results

@router.get(
    "/gaps/detail",
    response_model=GapDetailAuditResponse,
    summary="Retrieve full calculation and evidence audit for an occupation, geography, and period",
)
def get_gap_detail_audit(
    nco_code: str = Query(..., description="Canonical NCO code (e.g. 7421.0301)"),
    district_code: str = Query(..., description="District code (e.g. MH_PUN)"),
    reporting_period: str = Query(..., description="Reporting period (YYYY-MM)"),
    db: Session = Depends(get_db),
) -> GapDetailAuditResponse:
    """Retrieve complete evidence lineage, calculation formulas, and limitations audit."""
    occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == nco_code).first()
    if not occ:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NCO code '{nco_code}' not found in reference taxonomy.",
        )

    demand = (
        db.query(DemandObservation)
        .filter(
            DemandObservation.nco_code == nco_code,
            DemandObservation.district_code == district_code,
            DemandObservation.reporting_period == reporting_period,
        )
        .first()
    )

    supply = (
        db.query(QualifiedSupplyEstimate)
        .filter(
            QualifiedSupplyEstimate.nco_code == nco_code,
            QualifiedSupplyEstimate.district_code == district_code,
            QualifiedSupplyEstimate.reporting_period == reporting_period,
        )
        .first()
    )

    training = (
        db.query(TrainingCapacityOutcome)
        .filter(
            TrainingCapacityOutcome.nco_code == nco_code,
            TrainingCapacityOutcome.district_code == district_code,
            TrainingCapacityOutcome.reporting_period == reporting_period,
        )
        .first()
    )

    demand_val = demand.demand_value if demand else None
    supply_val = supply.supply_value if supply else None
    training_seats = training.sanctioned_seats if training else None

    assessment = assess_evidence_compatibility(
        demand_val=demand_val,
        demand_period=demand.reporting_period if demand else None,
        demand_district=demand.district_code if demand else None,
        demand_status=demand.data_status if demand else None,
        supply_val=supply_val,
        supply_period=supply.reporting_period if supply else None,
        supply_district=supply.district_code if supply else None,
        supply_status=supply.data_status if supply else None,
        unresolved_postings=demand.unresolved_postings_count if demand else 0,
        rejected_postings=demand.rejected_postings_count if demand else 0,
        training_seats=training_seats,
    )

    zero_demand_note = None
    if assessment.evidence_status == "CALCULATED" and demand_val is not None and supply_val is not None:
        abs_gap = calculate_absolute_gap(demand_val, supply_val)
        gap_rate, zero_demand_note = calculate_gap_rate(demand_val, supply_val)
        formula_used = "Absolute Gap = Demand − Qualified Supply; Gap Rate = ((Demand − Supply) / Demand) * 100"
    else:
        abs_gap = None
        gap_rate = None
        formula_used = "Calculation suppressed: Evidence incomplete or incompatible."

    return GapDetailAuditResponse(
        nco_code=occ.nco_code,
        canonical_title=occ.canonical_title,
        division_code=occ.division_code,
        division_title=occ.division_title,
        district_code=district_code,
        reporting_period=reporting_period,
        demand_value=demand_val,
        demand_unit=demand.unit if demand else None,
        demand_source=demand.source_system if demand else None,
        demand_method=demand.observation_method if demand else None,
        demand_status=demand.data_status if demand else None,
        unresolved_postings_count=demand.unresolved_postings_count if demand else 0,
        rejected_postings_count=demand.rejected_postings_count if demand else 0,
        supply_value=supply_val,
        supply_unit=supply.unit if supply else None,
        supply_source=supply.source_name if supply else None,
        supply_method=supply.estimation_method if supply else None,
        supply_status=supply.data_status if supply else None,
        confidence_interval_low=supply.confidence_interval_low if supply else None,
        confidence_interval_high=supply.confidence_interval_high if supply else None,
        sanctioned_training_seats=training_seats,
        training_capacity_caveat=(
            "Sanctioned training seats represent approved institutional intake capacity, NOT active available workers in the labour market."
            if training_seats is not None
            else None
        ),
        absolute_gap=abs_gap,
        gap_rate_pct=gap_rate,
        zero_demand_note=zero_demand_note,
        formula_used=formula_used,
        evidence_status=assessment.evidence_status,
        combined_data_status=assessment.combined_data_status,
        limitations=assessment.limitations,
        is_suitable_for_planning=assessment.is_suitable_for_planning,
        transparency_notice=assessment.transparency_notice,
    )

@router.post(
    "/seed-baseline",
    summary="Seed demonstration baseline analytics data (calibrated to Master R&D illustrative figures)",
)
def seed_baseline(db: Session = Depends(get_db)):
    """Seed synthetic demonstration baseline demand observations, supply estimates, and training capacity."""
    result = seed_pilot_baseline_analytics(db)
    return {
        "status": "COMPLETED",
        "provenance": "SYNTHETIC_DEMO",
        "demand_observations_added": result["demand_observations_added"],
        "supply_estimates_added": result["supply_estimates_added"],
        "training_capacity_added": result["training_capacity_added"],
        "message": "Synthetic demonstration baseline analytics data seeded successfully.",
    }

