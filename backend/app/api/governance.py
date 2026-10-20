"""Governance and Explainability API Endpoints (Phase 12)."""

import json
from typing import Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.audit_service import (
    query_audit_events,
    get_explainability_topic,
    list_all_explainability_topics,
)

router = APIRouter(prefix="/governance", tags=["Governance & Explainability"])


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    action_summary: str
    details: Any = None
    prev_hash: str | None = None
    record_hash: str | None = None
    created_at: str


@router.get(
    "/audit-logs",
    response_model=list[AuditEventResponse],
    summary="Query system-wide immutable audit logs",
)
def get_audit_logs(
    event_type: str | None = Query(None, description="Filter by event type"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[AuditEventResponse]:
    """Retrieve chronologically ordered audit logs with details and actors."""
    events = query_audit_events(db, event_type=event_type, entity_type=entity_type, limit=limit, offset=offset)
    return [
        AuditEventResponse(
            id=e.id,
            event_id=e.event_id,
            event_type=e.event_type,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            actor=e.actor,
            action_summary=e.action_summary,
            details=json.loads(e.details_json) if e.details_json else None,
            prev_hash=e.prev_hash,
            record_hash=e.record_hash,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in events
    ]


@router.get(
    "/audit-logs/verify",
    summary="Cryptographically verify unbroken SHA-256 hash continuity of entire audit trail",
)
def verify_audit_trail(db: Session = Depends(get_db)):
    """Traverse all audit records from genesis and detect any unauthorized alteration, deletion, or reordering."""
    from backend.app.services.audit_service import verify_audit_log_integrity
    return verify_audit_log_integrity(db)


@router.get(
    "/explainability",
    summary="List all explainability topics available in the knowledge engine",
)
def list_topics():
    """Return available explainability topics."""
    return {
        "available_topics": list_all_explainability_topics(),
        "disclaimer": "All calculations and rules are fully reproducible and mathematically documented in accordance with LMIS analytical requirements.",
    }


@router.get(
    "/explainability/{topic}",
    summary="Retrieve detailed mathematical and policy explainability dossier for a topic",
)
def get_topic_dossier(topic: str):
    """Retrieve detailed explainability dossier for forecasting, gaps, alerts, or recommendations."""
    dossier = get_explainability_topic(topic.lower())
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Explainability topic '{topic}' not found. Available topics: {list_all_explainability_topics()}",
        )
    return dossier
