"""Early-Warning Alerts generation and query service.

Conforms strictly to LMIS Master R&D Section 11:
- Four alert categories: Shortage Risk, Oversupply Risk, Emerging Demand, Data Quality Warning.
- Documented prototype thresholds explicitly marked as CONFIGURABLE_PROTOTYPE_DEFAULT.
- Insufficient evidence triggers DATA_QUALITY_WARNING rather than misleading shortage alarms.
- Provides actionable review suggestions for authorized human planners.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.analytics import (
    DemandObservation,
    QualifiedSupplyEstimate,
)
from backend.app.models.alerts import EarlyWarningAlert
from backend.app.models.forecasting import ForecastRun, ForecastPoint
from backend.app.models.occupation import NcoOccupation
from backend.app.schemas.alerts import (
    EarlyWarningAlertItem,
    AlertEvaluationResponse,
)
from backend.app.services.gap_calculator import (
    assess_evidence_compatibility,
    calculate_absolute_gap,
    calculate_gap_rate,
)

# Documented prototype thresholds (Master R&D Section 11)
DEFAULT_SHORTAGE_CRITICAL_GAP_RATE = 35.0  # % gap rate for CRITICAL severity
DEFAULT_SHORTAGE_WARNING_GAP_RATE = 20.0   # % gap rate for WARNING severity
DEFAULT_SHORTAGE_CRITICAL_ABSOLUTE = 250    # absolute shortage count for CRITICAL
DEFAULT_OVERSUPPLY_GAP_RATE = -15.0        # % gap rate for OVERSUPPLY warning
DEFAULT_OVERSUPPLY_ABSOLUTE = -100         # surplus count for OVERSUPPLY warning
DEFAULT_EMERGING_GROWTH_RATE = 15.0        # % hiring velocity growth


def evaluate_and_generate_alerts(db: Session) -> AlertEvaluationResponse:
    """Run rule-based early warning evaluation across latest observations."""
    # 1. Fetch all latest demand observations
    demand_records = db.query(DemandObservation).all()
    # Key by (nco_code, district_code, reporting_period)
    demand_map = {
        (d.nco_code, d.district_code, d.reporting_period): d
        for d in demand_records
    }

    # 2. Fetch all supply estimates
    supply_records = db.query(QualifiedSupplyEstimate).all()
    supply_map = {
        (s.nco_code, s.district_code, s.reporting_period): s
        for s in supply_records
    }

    # 3. Fetch occupation titles
    occupations = {o.nco_code: o.canonical_title for o in db.query(NcoOccupation).all()}

    # All unique keys
    all_keys = set(demand_map.keys()) | set(supply_map.keys())

    evaluated_alerts: list[EarlyWarningAlert] = []

    for nco_code, district, period in all_keys:
        d = demand_map.get((nco_code, district, period))
        s = supply_map.get((nco_code, district, period))

        title = occupations.get(nco_code, f"Occupation {nco_code}")
        demand_val = d.demand_value if d else None
        supply_val = s.supply_value if s else None

        unresolved = d.unresolved_postings_count if d else 0
        rejected = d.rejected_postings_count if d else 0

        # Assess evidence compatibility
        assessment = assess_evidence_compatibility(
            demand_val=demand_val,
            demand_period=d.reporting_period if d else None,
            demand_district=d.district_code if d else None,
            demand_status=d.data_status if d else None,
            supply_val=supply_val,
            supply_period=s.reporting_period if s else None,
            supply_district=s.district_code if s else None,
            supply_status=s.data_status if s else None,
            unresolved_postings=unresolved,
            rejected_postings=rejected,
        )

        # Case A: Incompatible or missing evidence -> DATA_QUALITY_WARNING
        if not assessment.is_suitable_for_planning or assessment.evidence_status != "CALCULATED":
            alert_id = f"ALT-DATA-{nco_code.replace('.', '')}-{district}-{period}"
            evaluated_alerts.append(
                EarlyWarningAlert(
                    alert_id=alert_id,
                    nco_code=nco_code,
                    canonical_title=title,
                    district_code=district,
                    reporting_period=period,
                    alert_type="DATA_QUALITY_WARNING",
                    severity="WARNING",
                    title=f"Data Quality Advisory: Incomplete Evidence in {title} ({district})",
                    trigger_rule=f"Status: {assessment.evidence_status}. Incomplete or unverified evidence prevents reliable equilibrium calculation.",
                    evidence_summary=assessment.transparency_notice,
                    review_action_recommended="Avoid policy decisions until missing hiring signals or qualified completion cohorts are imported.",
                    observed_demand=float(demand_val) if demand_val is not None else None,
                    estimated_supply=float(supply_val) if supply_val is not None else None,
                    absolute_gap=None,
                    gap_rate_pct=None,
                    threshold_type="DATA_AUDIT_RULE",
                    data_status=assessment.combined_data_status,
                    limitations="; ".join(assessment.limitations),
                )
            )
            continue

        # Case B: Calculated gap exists
        abs_gap = calculate_absolute_gap(demand_val, supply_val)
        gap_rate, _ = calculate_gap_rate(demand_val, supply_val)


        # Rule 1: SHORTAGE_RISK
        if abs_gap is not None and abs_gap > 0 and gap_rate is not None and gap_rate >= DEFAULT_SHORTAGE_WARNING_GAP_RATE:
            is_critical = gap_rate >= DEFAULT_SHORTAGE_CRITICAL_GAP_RATE or abs_gap >= DEFAULT_SHORTAGE_CRITICAL_ABSOLUTE
            severity = "CRITICAL" if is_critical else "WARNING"
            alert_id = f"ALT-SHRT-{nco_code.replace('.', '')}-{district}-{period}"

            evaluated_alerts.append(
                EarlyWarningAlert(
                    alert_id=alert_id,
                    nco_code=nco_code,
                    canonical_title=title,
                    district_code=district,
                    reporting_period=period,
                    alert_type="SHORTAGE_RISK",
                    severity=severity,
                    title=f"{'Severe' if is_critical else 'Potential'} Labour Shortage Risk: {title} ({district})",
                    trigger_rule=(
                        f"Prototype default rule: Gap Rate >= {DEFAULT_SHORTAGE_CRITICAL_GAP_RATE if is_critical else DEFAULT_SHORTAGE_WARNING_GAP_RATE}% "
                        f"(Observed: {gap_rate:.1f}%, Shortage: {abs_gap} workers)."
                    ),
                    evidence_summary=(
                        f"Demand ({demand_val}) exceeds estimated qualified supply ({supply_val}) by {abs_gap} workers "
                        f"(Gap Rate: {gap_rate:.1f}%). Hiring signals outpace local institutional completion pipelines."
                    ),
                    review_action_recommended=(
                        "Review whether additional accredited training seats, PMKVY short-term batches, "
                        "or industry apprenticeship tie-ups are justified for this district."
                    ),
                    observed_demand=float(demand_val),
                    estimated_supply=float(supply_val),
                    absolute_gap=float(abs_gap),
                    gap_rate_pct=float(gap_rate),
                    threshold_type="CONFIGURABLE_PROTOTYPE_DEFAULT",
                    data_status=assessment.combined_data_status,
                    limitations="; ".join(assessment.limitations),
                )
            )

        # Rule 2: OVERSUPPLY_RISK
        elif abs_gap is not None and (abs_gap <= DEFAULT_OVERSUPPLY_ABSOLUTE or (gap_rate is not None and gap_rate <= DEFAULT_OVERSUPPLY_GAP_RATE)):
            alert_id = f"ALT-OVR-{nco_code.replace('.', '')}-{district}-{period}"
            evaluated_alerts.append(
                EarlyWarningAlert(
                    alert_id=alert_id,
                    nco_code=nco_code,
                    canonical_title=title,
                    district_code=district,
                    reporting_period=period,
                    alert_type="OVERSUPPLY_RISK",
                    severity="WARNING",
                    title=f"Certification Surplus / Oversupply Risk: {title} ({district})",
                    trigger_rule=(
                        f"Prototype default rule: Supply exceeds demand by >= {abs(DEFAULT_OVERSUPPLY_ABSOLUTE)} workers "
                        f"or Gap Rate <= {DEFAULT_OVERSUPPLY_GAP_RATE}% (Observed Gap: {abs_gap}, Rate: {gap_rate:.1f}%)."
                    ),
                    evidence_summary=(
                        f"Estimated qualified supply ({supply_val}) exceeds observed demand ({demand_val}) "
                        f"by {abs(abs_gap)} workers. High institutional turnout relative to confirmed local postings."
                    ),
                    review_action_recommended=(
                        "Review upcoming seat allocations; evaluate curriculum transition towards specialized "
                        "high-demand niches or adjacent trade certifications to reduce unemployment friction."
                    ),
                    observed_demand=float(demand_val),
                    estimated_supply=float(supply_val),
                    absolute_gap=float(abs_gap),
                    gap_rate_pct=float(gap_rate),
                    threshold_type="CONFIGURABLE_PROTOTYPE_DEFAULT",
                    data_status=assessment.combined_data_status,
                    limitations="; ".join(assessment.limitations),
                )
            )

        # Rule 3: EMERGING_DEMAND (hiring velocity)
        if demand_val is not None and demand_val >= 600:
            alert_id = f"ALT-EMRG-{nco_code.replace('.', '')}-{district}-{period}"
            evaluated_alerts.append(
                EarlyWarningAlert(
                    alert_id=alert_id,
                    nco_code=nco_code,
                    canonical_title=title,
                    district_code=district,
                    reporting_period=period,
                    alert_type="EMERGING_DEMAND",
                    severity="INFO",
                    title=f"High Volume Demand Trajectory: {title} ({district})",
                    trigger_rule="Prototype rule: Confirmed monthly postings volume exceeds 600 vacancies.",
                    evidence_summary=f"Strong employer demand registered ({demand_val} vacancies).",
                    review_action_recommended="Monitor local faculty readiness and equipment availability in district training centres.",
                    observed_demand=float(demand_val),
                    estimated_supply=float(supply_val) if supply_val else None,
                    absolute_gap=float(abs_gap) if abs_gap else None,
                    gap_rate_pct=float(gap_rate) if gap_rate else None,
                    threshold_type="CONFIGURABLE_PROTOTYPE_DEFAULT",
                    data_status=assessment.combined_data_status,
                    limitations="; ".join(assessment.limitations),
                )
            )

    # Rule 4: FORECAST-DRIVEN EARLY-WARNING ALERTS (Projected Shortage & Oversupply)
    # Evaluates forward-looking horizon projections against latest supply benchmarks.
    # Strictly distinguishes prospective projected risks from observed historical shortages.
    forecast_runs = (
        db.query(ForecastRun)
        .filter(
            ForecastRun.target_metric == "DEMAND",
            ForecastRun.evaluation_status == "EVALUATED",
        )
        .order_by(desc(ForecastRun.created_at))
        .all()
    )

    # De-duplicate to ensure only the latest forecast run per (nco_code, district_code) is evaluated
    latest_forecast_runs: dict[tuple[str, str], ForecastRun] = {}
    for r in forecast_runs:
        key = (r.nco_code, r.district_code)
        if key not in latest_forecast_runs:
            latest_forecast_runs[key] = r

    for run in latest_forecast_runs.values():
        nco_code = run.nco_code
        district = run.district_code
        title = occupations.get(nco_code, f"Occupation {nco_code}")

        # Find latest available qualified supply estimate for this trade and district
        latest_supply = (
            db.query(QualifiedSupplyEstimate)
            .filter(
                QualifiedSupplyEstimate.nco_code == nco_code,
                QualifiedSupplyEstimate.district_code == district,
            )
            .order_by(desc(QualifiedSupplyEstimate.reporting_period))
            .first()
        )
        if not latest_supply or latest_supply.supply_value is None or latest_supply.supply_value <= 0:
            continue

        supply_val = float(latest_supply.supply_value)

        # Inspect projections across horizon steps
        for pt in run.points:
            if not pt.is_projection:
                continue

            proj_demand = float(pt.forecast_value)
            proj_gap = round(proj_demand - supply_val, 2)
            proj_gap_rate = round((proj_gap / proj_demand) * 100.0, 2) if proj_demand > 0 else 0.0

            # Sub-rule 4A: Projected Shortage Risk
            if proj_gap > 0 and proj_gap_rate >= DEFAULT_SHORTAGE_WARNING_GAP_RATE:
                is_critical = (
                    proj_gap_rate >= DEFAULT_SHORTAGE_CRITICAL_GAP_RATE
                    or proj_gap >= DEFAULT_SHORTAGE_CRITICAL_ABSOLUTE
                )
                severity = "CRITICAL" if is_critical else "WARNING"
                alert_id = f"ALT-PRJ-SHRT-{nco_code.replace('.', '')}-{district}-{pt.period}"

                ci_note = (
                    f"Approximate 80% CI: [{pt.lower_bound}, {pt.upper_bound}]"
                    if pt.lower_bound is not None and pt.upper_bound is not None
                    else "Uncertainty interval not computed"
                )

                evaluated_alerts.append(
                    EarlyWarningAlert(
                        alert_id=alert_id,
                        nco_code=nco_code,
                        canonical_title=title,
                        district_code=district,
                        reporting_period=pt.period,
                        alert_type="PROJECTED_SHORTAGE_RISK",
                        severity=severity,
                        title=f"{'Severe' if is_critical else 'Potential'} Projected Labour Shortage ({pt.period}): {title} ({district})",
                        trigger_rule=(
                            f"Forecast projection rule: {run.selected_model_name} predicts demand of {proj_demand:.0f} "
                            f"vs latest supply of {supply_val:.0f} (Projected Gap: +{proj_gap:.0f}, Rate: {proj_gap_rate:.1f}%). {ci_note}."
                        ),
                        evidence_summary=(
                            f"Forward time-series projection indicates prospective deficit of {proj_gap:.0f} qualified workers "
                            f"for period {pt.period} (Step +{pt.step_ahead}). Provenance: {run.data_status}. Model: {run.selected_model_name}."
                        ),
                        review_action_recommended=(
                            f"Review vocational intake, PMKVY short-term batches, or employer apprenticeship programs "
                            f"before {pt.period} to prevent forecasted hiring bottleneck."
                        ),
                        observed_demand=proj_demand,
                        estimated_supply=supply_val,
                        absolute_gap=proj_gap,
                        gap_rate_pct=proj_gap_rate,
                        threshold_type="FORECAST_PROJECTION_RULE",
                        data_status=run.data_status,
                        limitations=run.limitations,
                    )
                )

            # Sub-rule 4B: Projected Oversupply Risk
            elif proj_gap <= DEFAULT_OVERSUPPLY_ABSOLUTE or (
                proj_gap_rate <= DEFAULT_OVERSUPPLY_GAP_RATE and proj_gap < 0
            ):
                alert_id = f"ALT-PRJ-OVR-{nco_code.replace('.', '')}-{district}-{pt.period}"
                evaluated_alerts.append(
                    EarlyWarningAlert(
                        alert_id=alert_id,
                        nco_code=nco_code,
                        canonical_title=title,
                        district_code=district,
                        reporting_period=pt.period,
                        alert_type="PROJECTED_OVERSUPPLY_RISK",
                        severity="WARNING",
                        title=f"Projected Certification Surplus / Oversupply ({pt.period}): {title} ({district})",
                        trigger_rule=(
                            f"Forecast projection rule: Latest supply of {supply_val:.0f} exceeds projected demand of {proj_demand:.0f} "
                            f"(Projected Surplus: {abs(proj_gap):.0f}, Rate: {proj_gap_rate:.1f}%)."
                        ),
                        evidence_summary=(
                            f"Forward time-series projection indicates institutional turnout exceeds expected hiring requirements "
                            f"by {abs(proj_gap):.0f} for period {pt.period} (Step +{pt.step_ahead}). Provenance: {run.data_status}."
                        ),
                        review_action_recommended=(
                            f"Review upcoming seat sanctions before {pt.period}; assess curriculum diversification into "
                            f"adjacent higher-demand competencies to prevent graduate underemployment."
                        ),
                        observed_demand=proj_demand,
                        estimated_supply=supply_val,
                        absolute_gap=proj_gap,
                        gap_rate_pct=proj_gap_rate,
                        threshold_type="FORECAST_PROJECTION_RULE",
                        data_status=run.data_status,
                        limitations=run.limitations,
                    )
                )

    # 4. Upsert evaluated alerts into DB with stale alert purge for idempotency
    evaluated_alerts_dict: dict[str, EarlyWarningAlert] = {a.alert_id: a for a in evaluated_alerts}
    unique_alerts = list(evaluated_alerts_dict.values())
    active_alert_ids = set(evaluated_alerts_dict.keys())

    # Delete stale alerts that are no longer produced by current evidence/projections
    existing_all = db.query(EarlyWarningAlert).all()
    for ea in existing_all:
        if ea.alert_id not in active_alert_ids:
            db.delete(ea)

    critical_c = 0
    warning_c = 0
    info_c = 0

    for alt in unique_alerts:
        existing = db.query(EarlyWarningAlert).filter(EarlyWarningAlert.alert_id == alt.alert_id).first()
        if existing:
            existing.severity = alt.severity
            existing.title = alt.title
            existing.trigger_rule = alt.trigger_rule
            existing.evidence_summary = alt.evidence_summary
            existing.review_action_recommended = alt.review_action_recommended
            existing.observed_demand = alt.observed_demand
            existing.estimated_supply = alt.estimated_supply
            existing.absolute_gap = alt.absolute_gap
            existing.gap_rate_pct = alt.gap_rate_pct
            existing.threshold_type = alt.threshold_type
            existing.data_status = alt.data_status
            existing.limitations = alt.limitations
        else:
            db.add(alt)

        if alt.severity == "CRITICAL":
            critical_c += 1
        elif alt.severity == "WARNING":
            warning_c += 1
        else:
            info_c += 1

    db.commit()

    # Query back all alerts sorted by severity (CRITICAL first, then WARNING, then INFO)
    db_alerts = db.query(EarlyWarningAlert).all()
    # Custom sort: CRITICAL -> 0, WARNING -> 1, INFO -> 2
    sev_rank = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    db_alerts.sort(key=lambda a: (sev_rank.get(a.severity, 3), -(a.absolute_gap or 0)))

    items = [
        EarlyWarningAlertItem(
            alert_id=a.alert_id,
            nco_code=a.nco_code,
            canonical_title=a.canonical_title,
            district_code=a.district_code,
            reporting_period=a.reporting_period,
            alert_type=a.alert_type,
            severity=a.severity,
            title=a.title,
            trigger_rule=a.trigger_rule,
            evidence_summary=a.evidence_summary,
            review_action_recommended=a.review_action_recommended,
            observed_demand=a.observed_demand,
            estimated_supply=a.estimated_supply,
            absolute_gap=a.absolute_gap,
            gap_rate_pct=a.gap_rate_pct,
            threshold_type=a.threshold_type,
            triage_status=getattr(a, "triage_status", "NEW") or "NEW",
            triage_note=getattr(a, "triage_note", None),
            data_status=a.data_status,
            limitations=a.limitations,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in db_alerts
    ]

    return AlertEvaluationResponse(
        total_alerts_evaluated=len(items),
        critical_count=critical_c,
        warning_count=warning_c,
        info_count=info_c,
        alerts=items,
        message=f"Rule-based alerts evaluated: {critical_c} Critical, {warning_c} Warning, {info_c} Info.",
    )

