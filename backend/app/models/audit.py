"""Audit Logging Database Model (Phase 12: Governance and Explainability).

Records cryptographic timestamps, actors, and detailed payloads for every
critical data mutation across ingestion, normalization, and intelligence recomputations.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from backend.app.db.base import Base


class AuditEvent(Base):
    """Immutable audit trail log for system and user-initiated data events."""

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    event_type = Column(String(50), index=True, nullable=False)  # INGESTION_IMPORT, REVIEW_DECISION, PIPELINE_RECOMPUTE, etc.
    entity_type = Column(String(50), index=True, nullable=False)  # BATCH, OCCUPATION, PIPELINE, SCENARIO
    entity_id = Column(String(100), index=True, nullable=False)
    actor = Column(String(100), nullable=False, default="SYSTEM")
    action_summary = Column(String(255), nullable=False)
    details_json = Column(Text, nullable=True)  # JSON payload of parameters, diffs, counts
    prev_hash = Column(String(64), nullable=True)  # SHA-256 hash of immediately preceding audit event
    record_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash of (prev_hash + canonical event payload)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_audit_event_type_created", "event_type", "created_at"),
    )
