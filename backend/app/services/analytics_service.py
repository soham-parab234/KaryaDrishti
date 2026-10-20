"""Analytics service for aggregating demand, managing supply estimates, and seeding pilot baselines."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.occupation import NcoOccupation, TitleMappingReview
from backend.app.models.ingestion import IngestedPostingRecord
from backend.app.models.analytics import (
    DemandObservation,
    QualifiedSupplyEstimate,
    TrainingCapacityOutcome,
)
from backend.app.schemas.analytics import DemandAggregationResponse
from backend.app.services.gap_calculator import (
    assess_evidence_compatibility,
    calculate_absolute_gap,
    calculate_gap_rate,
)

PILOT_BASELINE_ANALYTICS = [
    {
        "nco_code": "7421.0301",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "demand_value": 680,
        "demand_source": "NCS_FEED",
        "supply_value": 420,
        "supply_source": "NCVET_COMPLETIONS_SYNTHESIS",
        "sanctioned_seats": 450,
        "enrolled": 410,
        "completions": 360,
        "placed": 345,
        "placement_rate": 72.5,
        "limitations": "Commercial rooftop installations in Chakan & Bhosari driving hiring velocity. Qualified supply lags demand due to accredited lab constraints.",
    },
    {
        "nco_code": "7421.0301",
        "district_code": "MH_NSK",
        "reporting_period": "2026-10",
        "demand_value": 290,
        "demand_source": "NCS_FEED",
        "supply_value": 275,
        "supply_source": "NCVET_COMPLETIONS_SYNTHESIS",
        "sanctioned_seats": 300,
        "enrolled": 280,
        "completions": 245,
        "placed": 238,
        "placement_rate": 68.0,
        "limitations": "Solar farm water-pumping installations aligned with local ITI capacity; minor seasonal post-monsoon surge.",
    },
    {
        "nco_code": "7233.0100",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "demand_value": 840,
        "demand_source": "PORTAL_SCRAPE",
        "supply_value": 510,
        "supply_source": "NCVET_COMPLETIONS_SYNTHESIS",
        "sanctioned_seats": 500,
        "enrolled": 480,
        "completions": 430,
        "placed": 405,
        "placement_rate": 78.2,
        "limitations": "Automotive Tier 1 plant expansions creating urgent maintenance technician deficit in Pimpri-Chinchwad.",
    },
    {
        "nco_code": "7233.0100",
        "district_code": "MH_NSK",
        "reporting_period": "2026-10",
        "demand_value": 410,
        "demand_source": "PORTAL_SCRAPE",
        "supply_value": 320,
        "supply_source": "NCVET_COMPLETIONS_SYNTHESIS",
        "sanctioned_seats": 350,
        "enrolled": 330,
        "completions": 290,
        "placed": 270,
        "placement_rate": 74.0,
        "limitations": "Ambad and Satpur MIDC manufacturing machine tool maintenance demand exceeds local vocational completers.",
    },
    {
        "nco_code": "3511.0101",
        "district_code": "MH_PUN",
        "reporting_period": "2026-10",
        "demand_value": 1250,
        "demand_source": "PORTAL_SCRAPE",
        "supply_value": 1480,
        "supply_source": "NCVET_COMPLETIONS_SYNTHESIS",
        "sanctioned_seats": 1200,
        "enrolled": 1150,
        "completions": 1080,
        "placed": 850,
        "placement_rate": 65.0,
        "limitations": "Routine back-office and entry-level IT operations face localized certification surplus due to high graduate turnout.",
    },
]

def seed_pilot_baseline_analytics(db: Session) -> dict[str, int]:
    """Seed synthetic demonstration baseline observations, supply estimates, and capacity outcomes calibrated to Master R&D Section 8."""
    demand_added = 0
    supply_added = 0
    capacity_added = 0

    for item in PILOT_BASELINE_ANALYTICS:
        nco_code = item["nco_code"]
        district = item["district_code"]
        period = item["reporting_period"]

        limitation_notice = (
            "NOTICE: Synthetic demonstration data calibrated to illustrative figures in Master R&D Section 8. "
            "Synthetic baseline numbers for pilot evaluation and testing, not live empirical census. "
            + item["limitations"]
        )

        # 1. Demand observation
        existing_demand = (
            db.query(DemandObservation)
            .filter(
                DemandObservation.nco_code == nco_code,
                DemandObservation.district_code == district,
                DemandObservation.reporting_period == period,
                DemandObservation.source_system == item["demand_source"],
            )
            .first()
        )
        if not existing_demand:
            db.add(
                DemandObservation(
                    nco_code=nco_code,
                    district_code=district,
                    reporting_period=period,
                    demand_value=item["demand_value"],
                    unit="OBSERVED_POSTINGS",
                    source_system=item["demand_source"],
                    observation_method="SYNTHETIC_DEMO_SAMPLE",
                    data_status="SYNTHETIC_DEMO",
                    unresolved_postings_count=0,
                    rejected_postings_count=0,
                    limitations=limitation_notice,
                )
            )
            demand_added += 1

        # 2. Qualified Supply estimate
        existing_supply = (
            db.query(QualifiedSupplyEstimate)
            .filter(
                QualifiedSupplyEstimate.nco_code == nco_code,
                QualifiedSupplyEstimate.district_code == district,
                QualifiedSupplyEstimate.reporting_period == period,
                QualifiedSupplyEstimate.source_name == item["supply_source"],
            )
            .first()
        )
        if not existing_supply:
            db.add(
                QualifiedSupplyEstimate(
                    nco_code=nco_code,
                    district_code=district,
                    reporting_period=period,
                    supply_value=item["supply_value"],
                    unit="QUALIFIED_WORKERS",
                    source_name=item["supply_source"],
                    estimation_method="SYNTHETIC_COHORT_SYNTHESIS",
                    data_status="SYNTHETIC_DEMO",
                    confidence_interval_low=int(item["supply_value"] * 0.92),
                    confidence_interval_high=int(item["supply_value"] * 1.08),
                    limitations=limitation_notice,
                )
            )
            supply_added += 1

        # 3. Training Capacity outcome
        existing_cap = (
            db.query(TrainingCapacityOutcome)
            .filter(
                TrainingCapacityOutcome.nco_code == nco_code,
                TrainingCapacityOutcome.district_code == district,
                TrainingCapacityOutcome.reporting_period == period,
                TrainingCapacityOutcome.source_system == "MSDE_NCVET_MIS",
            )
            .first()
        )
        if not existing_cap:
            db.add(
                TrainingCapacityOutcome(
                    nco_code=nco_code,
                    district_code=district,
                    reporting_period=period,
                    sanctioned_seats=item["sanctioned_seats"],
                    enrolled_students=item["enrolled"],
                    completed_students=item["completions"],
                    placed_students=item["placed"],
                    placement_rate_pct=item["placement_rate"],
                    source_system="MSDE_NCVET_MIS",
                    data_status="SYNTHETIC_DEMO",
                    limitations="Synthetic demonstration data: Sanctioned seats reflect approved ITI/PMKVY training capacity, not active labour market supply.",
                )
            )
            capacity_added += 1

    db.commit()
    return {
        "demand_observations_added": demand_added,
        "supply_estimates_added": supply_added,
        "training_capacity_added": capacity_added,
    }

def aggregate_demand_from_postings(
    db: Session,
    batch_id: str | None = None,
) -> DemandAggregationResponse:
    """Aggregate confirmed demand observations from approved title mapping reviews.

    Guardrails:
    - Only postings with status == 'APPROVED' contribute to confirmed demand.
    - Postings with status == 'PROPOSED', 'UNMATCHED', or 'REJECTED' are excluded from
      confirmed demand, but counted and disclosed in metadata.
    """
    base_query = db.query(IngestedPostingRecord, TitleMappingReview).join(
        TitleMappingReview,
        IngestedPostingRecord.id == TitleMappingReview.posting_record_id,
    )

    if batch_id:
        base_query = base_query.filter(IngestedPostingRecord.batch_id == batch_id)

    pairs = base_query.all()

    if not pairs:
        return DemandAggregationResponse(
            total_approved_postings_aggregated=0,
            unresolved_postings_excluded=0,
            rejected_postings_excluded=0,
            observations_created_or_updated=0,
            message="No ingested postings with title mapping records found.",
        )

    # Group postings by (nco_code, district_code, period, source_system)
    approved_groups: dict[tuple[str, str, str, str], int] = {}
    unresolved_groups: dict[tuple[str, str, str, str], int] = {}
    rejected_groups: dict[tuple[str, str, str, str], int] = {}

    total_approved = 0
    total_unresolved = 0
    total_rejected = 0

    for posting, review in pairs:
        # Determine period (YYYY-MM from observation_date)
        period = posting.observation_date[:7] if posting.observation_date else "2026-10"
        district = posting.district_code
        source = posting.source_system
        nco_code = review.proposed_nco_code

        if review.status == "REJECTED":
            if nco_code:
                group_key = (nco_code, district, period, source)
                rejected_groups[group_key] = rejected_groups.get(group_key, 0) + 1
            total_rejected += 1
            continue

        if not nco_code:
            # Unmatched or unassigned without approval
            total_unresolved += 1
            continue

        group_key = (nco_code, district, period, source)

        if review.status == "APPROVED":
            vacancies = posting.vacancy_count or 1
            approved_groups[group_key] = approved_groups.get(group_key, 0) + vacancies
            total_approved += vacancies
        else:  # PROPOSED or UNMATCHED
            unresolved_groups[group_key] = unresolved_groups.get(group_key, 0) + 1
            total_unresolved += 1

    # Upsert into DemandObservation
    obs_count = 0
    for (nco_code, district, period, source), demand_sum in approved_groups.items():
        unresolved_count = unresolved_groups.get((nco_code, district, period, source), 0)
        rejected_count = rejected_groups.get((nco_code, district, period, source), 0)

        existing = (
            db.query(DemandObservation)
            .filter(
                DemandObservation.nco_code == nco_code,
                DemandObservation.district_code == district,
                DemandObservation.reporting_period == period,
                DemandObservation.source_system == source,
            )
            .first()
        )

        limitation_text = f"Aggregated from {demand_sum} approved job postings via {source}."
        if unresolved_count > 0:
            limitation_text += f" ({unresolved_count} unapproved posting(s) excluded pending review)."

        if existing:
            existing.demand_value = demand_sum
            existing.unresolved_postings_count = unresolved_count
            existing.rejected_postings_count = rejected_count
            existing.limitations = limitation_text
            existing.observation_method = "APPROVED_MAPPINGS_AGGREGATION"
            existing.data_status = "IMPORTED"
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(
                DemandObservation(
                    nco_code=nco_code,
                    district_code=district,
                    reporting_period=period,
                    demand_value=demand_sum,
                    unit="OBSERVED_POSTINGS",
                    source_system=source,
                    observation_method="APPROVED_MAPPINGS_AGGREGATION",
                    data_status="IMPORTED",
                    unresolved_postings_count=unresolved_count,
                    rejected_postings_count=rejected_count,
                    limitations=limitation_text,
                )
            )
        obs_count += 1

    db.commit()

    return DemandAggregationResponse(
        total_approved_postings_aggregated=total_approved,
        unresolved_postings_excluded=total_unresolved,
        rejected_postings_excluded=total_rejected,
        observations_created_or_updated=obs_count,
        message=(
            f"Successfully aggregated {total_approved} confirmed vacancies across {obs_count} demand observation(s). "
            f"Excluded {total_unresolved} unresolved and {total_rejected} rejected postings."
        ),
    )
