"""SQLAlchemy models for NCO-2015 reference taxonomy, aliases, and title mapping reviews.

Conforms strictly to Directorate General of Employment (DGE) NCO-2015
hierarchical structure and LMIS Master R&D Section 7.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class NcoOccupation(Base):
    """Authoritative NCO-2015 reference occupation code and classification hierarchy."""

    __tablename__ = "nco_occupations"

    nco_code: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    canonical_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    division_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    division_title: Mapped[str] = mapped_column(String(255), nullable=False)
    sub_major_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sub_major_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    minor_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    minor_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_group_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    unit_group_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_status: Mapped[str] = mapped_column(String(50), default="PILOT_BASELINE", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    aliases: Mapped[list["OccupationAlias"]] = relationship(
        "OccupationAlias",
        back_populates="occupation",
        cascade="all, delete-orphan",
    )

class OccupationAlias(Base):
    """Known, verified alternative job titles mapped to an NCO occupation code."""

    __tablename__ = "occupation_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nco_code: Mapped[str] = mapped_column(String(20), ForeignKey("nco_occupations.nco_code"), nullable=False, index=True)
    alias_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), default="PILOT_CURATED", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    occupation: Mapped["NcoOccupation"] = relationship("NcoOccupation", back_populates="aliases")

class TitleMappingReview(Base):
    """Audit record and human-in-the-loop review item for a raw vacancy title mapping proposal."""

    __tablename__ = "title_mapping_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    posting_record_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingested_posting_records.id"), nullable=True, index=True
    )
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    raw_title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    proposed_nco_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("nco_occupations.nco_code"), nullable=True, index=True
    )
    proposed_canonical_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_method: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    match_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PROPOSED", nullable=False, index=True)
    reviewer_decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
