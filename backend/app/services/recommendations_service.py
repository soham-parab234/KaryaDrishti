"""Policy & Workforce Recommendation Generation Service (Phase 10: Decision Intelligence).

Generates practical, explainable training and workforce recommendations based on:
1. Observed demand-supply gap calculations and mismatch ratios.
2. Holt state-space forecast trajectories and trend velocity.
3. Institutional training capacities (sanctioned seats, placement rates).
4. Rigorous provenance and data completeness auditing.

Four core archetypes are supported:
- TRAINING_CAPACITY_EXPANSION: Long-term institutional seat scaling for persistent shortages.
- CURRICULUM_MODERNIZATION_OR_PIVOT: Realignment and seat reallocation for persistent surplus/stagnation.
- APPRENTICESHIP_INDUSTRY_TIE_UP: Rapid dual work-study pathways for high-velocity emerging demand.
- DATA_COLLECTION_AUDIT: Precautionary advisory when data is synthetic, incomplete, or unverified.
"""

import json
import math
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.analytics import (
    DemandObservation,
    QualifiedSupplyEstimate,
    TrainingCapacityOutcome,
)
from backend.app.models.forecasting import ForecastRun
from backend.app.models.occupation import NcoOccupation
from backend.app.models.recommendations import PolicyRecommendation
from backend.app.schemas.recommendations import (
    PolicyRecommendationItem,
    RecommendationListResponse,
)


def generate_policy_recommendations(db: Session) -> RecommendationListResponse:
    """Evaluate all current labour market evidence and generate explainable policy recommendations."""
    occupations = {o.nco_code: o.canonical_title for o in db.query(NcoOccupation).all()}

    # 1. Fetch latest demand observations per (nco_code, district_code)
    all_demands = db.query(DemandObservation).order_by(desc(DemandObservation.reporting_period)).all()
    latest_demand_map: dict[tuple[str, str], DemandObservation] = {}
    for d in all_demands:
        k = (d.nco_code, d.district_code)
        if k not in latest_demand_map:
            latest_demand_map[k] = d

    # 2. Fetch latest supply estimates per (nco_code, district_code)
    all_supplies = db.query(QualifiedSupplyEstimate).order_by(desc(QualifiedSupplyEstimate.reporting_period)).all()
    latest_supply_map: dict[tuple[str, str], QualifiedSupplyEstimate] = {}
    for s in all_supplies:
        k = (s.nco_code, s.district_code)
        if k not in latest_supply_map:
            latest_supply_map[k] = s

    # 3. Fetch latest training capacities per (nco_code, district_code)
    all_capacities = db.query(TrainingCapacityOutcome).order_by(desc(TrainingCapacityOutcome.reporting_period)).all()
    latest_cap_map: dict[tuple[str, str], TrainingCapacityOutcome] = {}
    for c in all_capacities:
        k = (c.nco_code, c.district_code)
        if k not in latest_cap_map:
            latest_cap_map[k] = c

    # 4. Fetch latest forecast runs per (nco_code, district_code)
    forecast_runs = (
        db.query(ForecastRun)
        .filter(ForecastRun.target_metric == "DEMAND", ForecastRun.evaluation_status == "EVALUATED")
        .order_by(desc(ForecastRun.created_at))
        .all()
    )
    latest_fcst_map: dict[tuple[str, str], ForecastRun] = {}
    for r in forecast_runs:
        k = (r.nco_code, r.district_code)
        if k not in latest_fcst_map:
            latest_fcst_map[k] = r

    # Determine universe of (nco_code, district_code) pairs
    all_universe = set(latest_demand_map.keys()) | set(latest_supply_map.keys()) | set(latest_fcst_map.keys())

    evaluated_recs: list[PolicyRecommendation] = []

    for nco_code, district_code in sorted(all_universe):
        title = occupations.get(nco_code, f"Occupation {nco_code}")
        d_obs = latest_demand_map.get((nco_code, district_code))
        s_obs = latest_supply_map.get((nco_code, district_code))
        cap_obs = latest_cap_map.get((nco_code, district_code))
        fcst_run = latest_fcst_map.get((nco_code, district_code))

        reporting_period = (
            d_obs.reporting_period if d_obs else (s_obs.reporting_period if s_obs else "2026-03")
        )

        demand_val = float(d_obs.demand_value) if d_obs and d_obs.demand_value is not None else None
        supply_val = float(s_obs.supply_value) if s_obs and s_obs.supply_value is not None else None
        sanctioned_seats = cap_obs.sanctioned_seats if cap_obs else 0

        # Check data quality & provenance
        is_synthetic = (
            (d_obs and d_obs.data_status == "SYNTHETIC_DEMO")
            or (s_obs and s_obs.data_status == "SYNTHETIC_DEMO")
        )
        unresolved_postings = d_obs.unresolved_postings_count if d_obs else 0
        total_postings = (d_obs.demand_value + unresolved_postings) if d_obs else 0
        high_unresolved_ratio = (
            unresolved_postings > 0 and total_postings > 0 and (unresolved_postings / total_postings) > 0.25
        )

        # Look up 3-month forecast step
        proj_3m_demand = None
        proj_lower = None
        proj_upper = None
        if fcst_run and fcst_run.points:
            proj_pts = [p for p in fcst_run.points if p.is_projection]
            if proj_pts:
                # Last projected point in horizon
                last_pt = proj_pts[-1]
                proj_3m_demand = float(last_pt.forecast_value)
                proj_lower = last_pt.lower_bound
                proj_upper = last_pt.upper_bound

        # ---------------------------------------------------------
        # Case A: DATA_COLLECTION_AUDIT
        # If evidence is predominantly synthetic, missing, or heavily unresolved
        # ---------------------------------------------------------
        if demand_val is None or supply_val is None or is_synthetic or high_unresolved_ratio or not fcst_run:
            slug = nco_code.replace(".", "")
            rec_id = f"REC-AUDIT-{slug}-{district_code}"
            
            reasons = []
            if demand_val is None:
                reasons.append("Missing confirmed employer demand observations")
            if supply_val is None:
                reasons.append("Missing certified supply estimates")
            if is_synthetic:
                reasons.append("Demand/supply metrics are based on synthetic baseline demonstration data")
            if high_unresolved_ratio:
                reasons.append(f"{unresolved_postings} unapproved job postings pending human review")
            if not fcst_run:
                reasons.append("Insufficient chronological time series history for forecasting")

            rationale_text = (
                f"Data integrity advisory: Capital expansion is deferred because the evidence base is incomplete or synthetic. "
                f"Specific issues identified: {'; '.join(reasons)}. "
                f"A targeted local field survey is required before committing public training infrastructure budgets."
            )

            evidence_dict = {
                "observed_demand": demand_val,
                "observed_supply": supply_val,
                "data_provenance": "SYNTHETIC_DEMO" if is_synthetic else "INCOMPLETE_EVIDENCE",
                "unresolved_postings": unresolved_postings,
                "forecast_available": fcst_run is not None,
            }

            limitations_list = [
                "Precautionary policy advisory: Do not allocate capital funds based on unverified or synthetic numbers.",
                "Action requires establishing contact with local industrial associations and employment exchanges.",
                "Survey findings must be vetted through the standard ingestion review queue.",
            ]

            evaluated_recs.append(
                PolicyRecommendation(
                    recommendation_id=rec_id,
                    nco_code=nco_code,
                    canonical_title=title,
                    district_code=district_code,
                    reporting_period=reporting_period,
                    recommendation_type="DATA_COLLECTION_AUDIT",
                    action_title=f"Commission District Employer & Tracer Survey for {title}",
                    priority="HIGH" if is_synthetic else "MEDIUM",
                    rationale=rationale_text,
                    evidence_sources=json.dumps(evidence_dict),
                    proposed_seat_adjustment=0,
                    target_horizon_months=3,
                    expected_impact_summary="Establishes empirical baseline to replace synthetic assumptions and calibrate institutional intake.",
                    feasibility_score=0.92,
                    data_status="DATA_DEFICIT_ADVISORY",
                    limitations=json.dumps(limitations_list),
                )
            )

        # ---------------------------------------------------------
        # Case B, C, D: EVIDENCE-BASED ACTION RECOMMENDATIONS
        # When empirical or hybrid demand and supply evidence is available
        # ---------------------------------------------------------
        if demand_val is not None and supply_val is not None:
            abs_gap = round(demand_val - supply_val, 1)
            gap_rate = round((abs_gap / demand_val) * 100.0, 1) if demand_val > 0 else 0.0
            
            # Forecast gap
            comp_demand = proj_3m_demand if proj_3m_demand is not None else demand_val
            proj_gap = round(comp_demand - supply_val, 1)
            growth_slope_pct = round(((comp_demand - demand_val) / demand_val) * 100.0, 1) if demand_val > 0 else 0.0

            evidence_dict = {
                "observed_demand": demand_val,
                "estimated_supply": supply_val,
                "absolute_gap": abs_gap,
                "gap_rate_pct": gap_rate,
                "projected_3m_demand": comp_demand,
                "projected_gap": proj_gap,
                "forecast_growth_slope_pct": growth_slope_pct,
                "existing_sanctioned_seats": sanctioned_seats,
                "confidence_interval_80": [proj_lower, proj_upper] if proj_lower is not None else None,
            }

            # 1. TRAINING_CAPACITY_EXPANSION
            # Trigger: Substantial observed shortage (gap > 0 and gap_rate >= 15%) and forecast shows persistent/expanding gap
            if abs_gap >= 30 and gap_rate >= 15.0 and proj_gap >= 30:
                slug = nco_code.replace(".", "")
                rec_id = f"REC-EXP-{slug}-{district_code}"
                
                # Formula yield factor from Master R&D:
                # 80% enrolment * 75% completion * 60% local entry = 0.36 net yield
                # Target: Close ~60% of projected gap
                target_closure = 0.60 * proj_gap
                calc_seats = int(round(target_closure / 0.36))
                proposed_seats = max(20, min(600, int(math.ceil(calc_seats / 10.0) * 10)))  # round up to nearest 10

                expected_graduates = round(proposed_seats * 0.36, 1)
                is_crit = abs_gap >= 150 or gap_rate >= 30.0

                rationale_text = (
                    f"Observed labour shortage of {abs_gap:+.0f} workers (mismatch rate {gap_rate:+.1f}%) "
                    f"is reinforced by Holt time-series projections forecasting {comp_demand:.0f} vacancies "
                    f"({proj_gap:+.0f} projected deficit at 3-month horizon). "
                    f"Current sanctioned training capacity of {sanctioned_seats} seats is insufficient to meet replacement and growth demand."
                )

                limitations_list = [
                    "Institutional lead time: New seat sanctions take 12 to 24 months to yield market entrants.",
                    f"Resource requirement: Requires ~{math.ceil(proposed_seats / 20)} certified instructor(s) and accredited workshop tooling.",
                    "Assumes standard student retention (75% completion) and local employment absorption (60%).",
                ]

                evaluated_recs.append(
                    PolicyRecommendation(
                        recommendation_id=rec_id,
                        nco_code=nco_code,
                        canonical_title=title,
                        district_code=district_code,
                        reporting_period=reporting_period,
                        recommendation_type="TRAINING_CAPACITY_EXPANSION",
                        action_title=f"Sanction +{proposed_seats} Additional ITI/Polytechnic Training Seats for {title}",
                        priority="HIGH" if is_crit else "MEDIUM",
                        rationale=rationale_text,
                        evidence_sources=json.dumps(evidence_dict),
                        proposed_seat_adjustment=proposed_seats,
                        target_horizon_months=12,
                        expected_impact_summary=f"Generates ~{expected_graduates} net qualified technicians annually, mitigating ~{round((expected_graduates/proj_gap)*100, 1)}% of the projected deficit.",
                        feasibility_score=0.78,
                        data_status="CONFIRMED_OBSERVATION" if not is_synthetic else "SYNTHETIC_DEMO",
                        limitations=json.dumps(limitations_list),
                    )
                )

            # 2. CURRICULUM_MODERNIZATION_OR_PIVOT
            # Trigger: Significant oversupply / surplus (gap <= -40 or gap_rate <= -15%)
            elif abs_gap <= -40 or gap_rate <= -15.0:
                slug = nco_code.replace(".", "")
                rec_id = f"REC-PVT-{slug}-{district_code}"

                reallocate_seats = -int(round(min(abs(abs_gap) * 0.4, sanctioned_seats * 0.3)))
                reallocate_seats = int(math.floor(reallocate_seats / 10.0) * 10) if reallocate_seats < 0 else 0

                rationale_text = (
                    f"Substantial labour surplus detected: Current qualified supply of {supply_val:.0f} "
                    f"exceeds demand of {demand_val:.0f} (Surplus: {abs_gap:+.0f}, Rate: {gap_rate:+.1f}%). "
                    f"Continuing unadjusted admissions produces graduates facing high local unabsorption. "
                    f"Recommendation: Modernize curriculum to integrate emerging industry modules or reallocate seats."
                )

                limitations_list = [
                    "Requires multi-stakeholder curriculum review with Sector Skill Council (SSC) and NCVET.",
                    "Faculty redeployment requires 4 to 8 weeks technical upskilling before new syllabus rollout.",
                    "Seat reallocation should be phased to prevent disruption for currently enrolled first-year batches.",
                ]

                evaluated_recs.append(
                    PolicyRecommendation(
                        recommendation_id=rec_id,
                        nco_code=nco_code,
                        canonical_title=title,
                        district_code=district_code,
                        reporting_period=reporting_period,
                        recommendation_type="CURRICULUM_MODERNIZATION_OR_PIVOT",
                        action_title=f"Modernize Training Curriculum & Pivot Capacity for {title}",
                        priority="MEDIUM",
                        rationale=rationale_text,
                        evidence_sources=json.dumps(evidence_dict),
                        proposed_seat_adjustment=reallocate_seats,
                        target_horizon_months=6,
                        expected_impact_summary="Curriculum enhancement and modular specialization to improve graduate employability from ~40% to ~70%.",
                        feasibility_score=0.82,
                        data_status="CONFIRMED_OBSERVATION" if not is_synthetic else "SYNTHETIC_DEMO",
                        limitations=json.dumps(limitations_list),
                    )
                )

            # 3. APPRENTICESHIP_INDUSTRY_TIE_UP
            # Trigger: Demand velocity is rapid (growth slope >= 10% or forecast demand growing fast)
            if growth_slope_pct >= 10.0 or (proj_gap > 0 and abs_gap > 0):
                slug = nco_code.replace(".", "")
                rec_id = f"REC-APP-{slug}-{district_code}"
                
                apprentice_slots = max(15, min(250, int(round(comp_demand * 0.25 / 5.0) * 5)))

                rationale_text = (
                    f"Forward-looking forecast projects hiring demand expanding by {growth_slope_pct:+.1f}% "
                    f"over the next quarter (Projected: {comp_demand:.0f} vacancies). "
                    f"Because formal vocational diploma expansion requires 1-2 years lead time, "
                    f"a dual work-study apprenticeship drive under NAPS / NATS provides rapid, industry-aligned talent delivery."
                )

                limitations_list = [
                    "Contingent on formal apprenticeship MoUs signed with local manufacturing/service clusters.",
                    "Requires stipend support under National Apprenticeship Promotion Scheme (NAPS).",
                    "Targeted trade requires workplace safety compliance verification before placement.",
                ]

                evaluated_recs.append(
                    PolicyRecommendation(
                        recommendation_id=rec_id,
                        nco_code=nco_code,
                        canonical_title=title,
                        district_code=district_code,
                        reporting_period=reporting_period,
                        recommendation_type="APPRENTICESHIP_INDUSTRY_TIE_UP",
                        action_title=f"Launch Fast-Track Dual Apprenticeship Tie-Up for {title}",
                        priority="HIGH" if growth_slope_pct >= 20.0 else "MEDIUM",
                        rationale=rationale_text,
                        evidence_sources=json.dumps(evidence_dict),
                        proposed_seat_adjustment=apprentice_slots,
                        target_horizon_months=4,
                        expected_impact_summary=f"Rapidly deploys ~{apprentice_slots} work-ready apprentices within 90-120 days, reducing immediate vacancy drag.",
                        feasibility_score=0.86,
                        data_status="PROJECTION_BASED",
                        limitations=json.dumps(limitations_list),
                    )
                )

    # De-duplicate by recommendation_id
    unique_recs_dict: dict[str, PolicyRecommendation] = {}
    for r in evaluated_recs:
        unique_recs_dict[r.recommendation_id] = r

    # Persist cleanly to database (delete stale recommendations and insert fresh)
    db.query(PolicyRecommendation).delete()
    for rec in unique_recs_dict.values():
        db.add(rec)
    db.commit()

    # Query all active recommendations for response
    active_recs = db.query(PolicyRecommendation).order_by(
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
        for r in active_recs
    ]

    expansion_c = sum(1 for i in items if i.recommendation_type == "TRAINING_CAPACITY_EXPANSION")
    pivot_c = sum(1 for i in items if i.recommendation_type == "CURRICULUM_MODERNIZATION_OR_PIVOT")
    app_c = sum(1 for i in items if i.recommendation_type == "APPRENTICESHIP_INDUSTRY_TIE_UP")
    audit_c = sum(1 for i in items if i.recommendation_type == "DATA_COLLECTION_AUDIT")

    return RecommendationListResponse(
        total_recommendations=len(items),
        expansion_count=expansion_c,
        curriculum_pivot_count=pivot_c,
        apprenticeship_count=app_c,
        data_audit_count=audit_c,
        items=items,
    )
