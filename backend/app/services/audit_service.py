"""Audit Logging and Algorithmic Explainability Service (Phase 12: Governance and Explainability).

Provides:
1. Cryptographic and chronological audit logging for all mutations across ingestion, normalization, and pipeline recomputations.
2. Mathematically grounded explainability documentation for all forecasting models, prediction intervals, gap formulas, and alert rules.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.audit import AuditEvent


def format_canonical_timestamp(dt: datetime | str | None) -> str:
    """Format datetime or string into canonical UTC ISO-8601 string (%Y-%m-%dT%H:%M:%SZ) for deterministic hashing."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return dt[:19]
    if isinstance(dt, datetime):
        utc_dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return utc_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(dt)


def compute_event_hash(
    prev_hash: str,
    event_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    action_summary: str,
    created_at_iso: str,
    details_json: str | None,
) -> str:
    """Compute canonical SHA-256 hash across event fields linked to previous record hash."""
    payload = f"{prev_hash}|{event_id}|{event_type}|{entity_type}|{entity_id}|{actor}|{action_summary}|{created_at_iso}|{details_json or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_audit_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    action_summary: str,
    actor: str = "SYSTEM",
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Record a cryptographically chained, tamper-evident audit log entry."""
    eid = f"AUD-{uuid.uuid4().hex[:12].upper()}"
    now_utc = datetime.now(timezone.utc)
    created_at_str = format_canonical_timestamp(now_utc)
    details_str = json.dumps(details, sort_keys=True) if details else None

    # Retrieve last event to establish hash chain link
    last_event = db.query(AuditEvent).order_by(desc(AuditEvent.id)).first()
    prev_hash = last_event.record_hash if (last_event and last_event.record_hash) else "0" * 64

    rec_hash = compute_event_hash(
        prev_hash=prev_hash,
        event_id=eid,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        action_summary=action_summary,
        created_at_iso=created_at_str,
        details_json=details_str,
    )

    event = AuditEvent(
        event_id=eid,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        action_summary=action_summary,
        details_json=details_str,
        prev_hash=prev_hash,
        record_hash=rec_hash,
        created_at=now_utc,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def verify_audit_log_integrity(db: Session) -> dict[str, Any]:
    """Traverse all audit events from genesis and mathematically verify cryptographic chain continuity and record hashes."""
    events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    if not events:
        return {
            "is_valid": True,
            "total_events": 0,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "details": "Audit log is empty; genesis state valid.",
        }

    expected_prev = "0" * 64
    for idx, e in enumerate(events):
        curr_prev = e.prev_hash or ("0" * 64)
        if curr_prev != expected_prev:
            return {
                "is_valid": False,
                "total_events": len(events),
                "corrupted_at_index": idx,
                "corrupted_event_id": e.event_id,
                "failure_reason": f"Chain link broken at event {e.event_id}: stored prev_hash ({curr_prev[:12]}...) does not match prior record_hash ({expected_prev[:12]}...).",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

        recomputed = compute_event_hash(
            prev_hash=curr_prev,
            event_id=e.event_id,
            event_type=e.event_type,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            actor=e.actor,
            action_summary=e.action_summary,
            created_at_iso=format_canonical_timestamp(e.created_at),
            details_json=e.details_json,
        )
        if e.record_hash and e.record_hash != recomputed:
            return {
                "is_valid": False,
                "total_events": len(events),
                "corrupted_at_index": idx,
                "corrupted_event_id": e.event_id,
                "failure_reason": f"Record modification detected at event {e.event_id}: stored record_hash does not match recomputed SHA-256 payload digest.",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

        expected_prev = e.record_hash or recomputed

    return {
        "is_valid": True,
        "total_events": len(events),
        "genesis_hash": events[0].record_hash,
        "head_hash": events[-1].record_hash,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "details": f"All {len(events)} audit events verified with unbroken SHA-256 cryptographic chain continuity.",
    }


def query_audit_events(
    db: Session,
    event_type: str | None = None,
    entity_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditEvent]:
    """Retrieve filtered audit history in reverse chronological order."""
    q = db.query(AuditEvent)
    if event_type:
        q = q.filter(AuditEvent.event_type == event_type)
    if entity_type:
        q = q.filter(AuditEvent.entity_type == entity_type)
    return q.order_by(desc(AuditEvent.id)).offset(offset).limit(limit).all()


# Algorithmic explainability encyclopaedia
EXPLAINABILITY_DOCS: dict[str, dict[str, Any]] = {
    "forecast_intervals": {
        "title": "Holt State-Space Prediction Interval Mathematics",
        "primary_reference": "Hyndman, R.J. & Athanasopoulos, G. (2021). Forecasting: Principles and Practice. Section 8.7.",
        "mathematical_formula": "sigma_h^2 = sigma^2 * [1 + sum_{j=1}^{h-1} (alpha + j * alpha * beta)^2]",
        "coverage_level": "80% Nominal Two-Sided Coverage (z = 1.282)",
        "assumptions": [
            "Errors e_t are conditionally normal with zero mean and constant residual variance sigma^2.",
            "Prediction variance compounds over forecast horizon steps h in proportion to smoothing parameter alpha and trend parameter beta.",
            "Physical Non-Negativity: Lower bounds are truncated at 0.0 because employer job vacancies cannot be negative.",
        ],
        "limitations": [
            "Intervals reflect state-space innovation variance but do not account for external macroeconomic shocks or structural policy regime changes.",
            "Short series (< 6 months) do not possess sufficient sample size to estimate reliable residual variance, prompting forecast suppression.",
        ],
    },
    "gap_formulas": {
        "title": "Demand-Supply Gap & Mismatch Metrics",
        "primary_reference": "LMIS Master R&D Section 8: Labour Market Balance Formulations",
        "mathematical_formula": "Absolute Gap = Demand - Qualified Supply; Gap Rate = ((Demand - Qualified Supply) / Demand) * 100",
        "data_compatibility_rules": [
            "Period Alignment: Both demand and supply must belong to identical calendar months.",
            "Geographic Alignment: Records must correspond to identical district boundaries (e.g. MH_PUN).",
            "Capacity vs. Supply: Sanctioned vocational training seats represent institutional capacity, NOT active qualified job seekers, and are strictly separated.",
            "Human Review Exclusion: Unapproved or rejected job postings are tracked separately and excluded from confirmed demand until reviewed.",
        ],
        "limitations": [
            "Gap rate is mathematically undefined when demand is zero or negative.",
            "Qualified supply pool estimates depend on empirical tracer studies or pilot baseline parameters.",
        ],
    },
    "alert_triggers": {
        "title": "Rule-Based Early Warning Alert Framework",
        "primary_reference": "LMIS Master R&D Section 11: Multi-Rule Early Warning Triggers",
        "rule_hierarchy": [
            "Rule 1: Observed Shortage Risk (CRITICAL if gap >= 250 or gap_rate >= 35%; WARNING if gap_rate >= 20%).",
            "Rule 2: Observed Oversupply Risk (WARNING if gap <= -100 or gap_rate <= -15%).",
            "Rule 3: Emerging Demand Surge (INFO if confirmed monthly vacancies exceed 600).",
            "Rule 4: Forward Forecast-Driven Shortage/Oversupply (Evaluates Holt h-step projections vs latest available supply benchmark).",
            "Rule 5: Data Quality Advisory (Triggers when evidence is incomplete, missing, or predominantly synthetic).",
        ],
        "limitations": [
            "Alert thresholds are configurable baseline defaults calibrated for district-level pilot trades.",
            "Projected alerts must always be evaluated in conjunction with the 80% prediction interval lower/upper bounds.",
        ],
    },
    "recommendation_logic": {
        "title": "Decision Intelligence Policy Recommendation Archetypes",
        "primary_reference": "LMIS Master R&D Section 10: Training Seat Conversion and Transition Dynamics",
        "archetypes": [
            "TRAINING_CAPACITY_EXPANSION: Derived when persistent shortages exceed current ITI capacity. Seat scaling targets 60% closure of residual gap using scenario yield factor (0.36 net yield).",
            "CURRICULUM_MODERNIZATION_OR_PIVOT: Derived when persistent surplus or high placement unabsorption indicates outdated vocational profiles.",
            "APPRENTICESHIP_INDUSTRY_TIE_UP: Fast-track dual work-study pathways under NAPS when forecast demand velocity outpaces multi-year institutional course cycles.",
            "DATA_COLLECTION_AUDIT: Precautionary advisory triggered when data provenance is synthetic or incomplete, preventing misallocation of public capital.",
        ],
        "limitations": [
            "All recommendations are decision-support guidelines requiring District Skill Committee and state finance concurrence.",
        ],
    },
}


def get_explainability_topic(topic: str) -> dict[str, Any] | None:
    """Retrieve transparent mathematical explainability dossier for a specified engine component."""
    return EXPLAINABILITY_DOCS.get(topic)


def list_all_explainability_topics() -> list[str]:
    """List available explainability documentation topics."""
    return list(EXPLAINABILITY_DOCS.keys())
