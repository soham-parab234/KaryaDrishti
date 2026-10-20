"""Demand–Supply Gap Calculation & Evidence Quality Evaluation Engine.

Conforms strictly to LMIS Master R&D Section 8:
- Absolute gap = Demand − Qualified Supply (positive = shortage, negative = oversupply).
- Gap rate = ((Demand − Qualified Supply) / Demand) * 100, when Demand > 0.
- When Demand == 0: Gap rate is mathematically undefined (returns None).
- Rejects calculation if demand and supply are from incompatible periods or geographies.
- Excluded unapproved/rejected postings are reported separately and never silently discarded.
- Sanctioned training seats represent capacity, NOT available supply.
"""

from dataclasses import dataclass, field

@dataclass
class EvidenceQualityAssessment:
    evidence_status: str  # "CALCULATED", "MISSING_SUPPLY", "MISSING_DEMAND", "INCOMPATIBLE_PERIOD_OR_GEOGRAPHY", "INSUFFICIENT_EVIDENCE"
    is_suitable_for_planning: bool
    combined_data_status: str
    limitations: list[str] = field(default_factory=list)
    transparency_notice: str = ""

def assess_evidence_compatibility(
    demand_val: int | None,
    demand_period: str | None,
    demand_district: str | None,
    demand_status: str | None,
    supply_val: int | None,
    supply_period: str | None,
    supply_district: str | None,
    supply_status: str | None,
    unresolved_postings: int = 0,
    rejected_postings: int = 0,
    training_seats: int | None = None,
) -> EvidenceQualityAssessment:
    """Evaluate temporal, geographic, and provenance compatibility between demand and supply."""
    limitations: list[str] = []

    # 1. Determine combined data status
    statuses = {s for s in (demand_status, supply_status) if s is not None}
    if not statuses:
        combined_status = "UNKNOWN"
    elif "SYNTHETIC_DEMO" in statuses:
        combined_status = "SYNTHETIC_DEMO"
    elif len(statuses) == 1:
        combined_status = list(statuses)[0]
    else:
        combined_status = "MIXED"

    # 2. Check for missing evidence
    if unresolved_postings > 0:
        limitations.append(
            f"{unresolved_postings} unapproved job posting(s) excluded from confirmed demand pending human review."
        )
    if rejected_postings > 0:
        limitations.append(
            f"{rejected_postings} job posting(s) excluded due to rejected occupation mappings."
        )

    if demand_val is None and supply_val is None:
        return EvidenceQualityAssessment(
            evidence_status="INSUFFICIENT_EVIDENCE",
            is_suitable_for_planning=False,
            combined_data_status=combined_status,
            limitations=["Both demand observation and qualified supply estimate are missing."] + limitations,
            transparency_notice="Insufficient evidence: Cannot evaluate labour market equilibrium without observations.",
        )

    if demand_val is None:
        return EvidenceQualityAssessment(
            evidence_status="MISSING_DEMAND",
            is_suitable_for_planning=False,
            combined_data_status=combined_status,
            limitations=["Observed demand signal is missing for this occupation, geography, and period."] + limitations,
            transparency_notice="Supply estimate is recorded, but employer demand signal is missing. Gap calculation suppressed.",
        )

    if supply_val is None:
        return EvidenceQualityAssessment(
            evidence_status="MISSING_SUPPLY",
            is_suitable_for_planning=False,
            combined_data_status=combined_status,
            limitations=["Qualified supply estimate is missing for this occupation, geography, and period."] + limitations,
            transparency_notice="Employer demand signal is recorded, but qualified worker supply is missing. Gap calculation suppressed.",
        )

    # 3. Check for temporal or geographic incompatibility
    if demand_period != supply_period or demand_district != supply_district:
        incompat_note = (
            f"Temporal/Geographic mismatch: Demand is recorded for ({demand_period}, {demand_district}) "
            f"while Supply is estimated for ({supply_period}, {supply_district}). "
            "Direct arithmetic comparison would be statistically misleading and is suppressed."
        )
        return EvidenceQualityAssessment(
            evidence_status="INCOMPATIBLE_PERIOD_OR_GEOGRAPHY",
            is_suitable_for_planning=False,
            combined_data_status=combined_status,
            limitations=[incompat_note] + limitations,
            transparency_notice=incompat_note,
        )

    # 4. Compatible evidence — document caveats and excluded postings
    if training_seats is not None:
        limitations.append(
            f"Sanctioned training seats ({training_seats}) represent institutional capacity, NOT active available qualified workers."
        )

    limitations.append(
        "Observed demand reflects documented hiring signals and does not claim to represent total macroeconomic vacancies."
    )

    if combined_status == "SYNTHETIC_DEMO":
        limitations.append(
            "NOTICE: Figures are based on synthetic demonstration data calibrated for Maharashtra pilot corridor."
        )

    return EvidenceQualityAssessment(
        evidence_status="CALCULATED",
        is_suitable_for_planning=True,
        combined_data_status=combined_status,
        limitations=limitations,
        transparency_notice="Demand and qualified supply evidence aligned by geography, period, and canonical NCO mapping.",
    )

def calculate_absolute_gap(demand: int, supply: int) -> int:
    """Compute absolute labour demand-supply gap.
    
    Formula: Demand − Qualified Supply
    Positive = Potential Shortage
    Negative = Potential Oversupply
    Zero = Equilibrium
    """
    return demand - supply

def calculate_gap_rate(demand: int, supply: int) -> tuple[float | None, str | None]:
    """Compute relative gap rate percentage according to Master R&D Section 8.
    
    Formula: ((Demand − Qualified Supply) / Demand) * 100, when Demand > 0.
    Returns: (gap_rate_pct, zero_demand_note)
    """
    if demand <= 0:
        return (
            None,
            "Undefined: Observed demand is zero in this reporting period. Gap rate division by zero is mathematically suppressed.",
        )

    absolute_gap = demand - supply
    rate = round((absolute_gap / demand) * 100, 1)
    return (rate, None)
