"""SQLAlchemy models for CSV ingestion batches and records."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ImportBatch(Base):
    """Metadata record for an uploaded and ingested batch file."""

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED", nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    records: Mapped[list["IngestedPostingRecord"]] = relationship(
        "IngestedPostingRecord",
        back_populates="batch",
        cascade="all, delete-orphan",
    )

class IngestedPostingRecord(Base):
    """Validated raw job posting observation ingested from an external CSV batch."""

    __tablename__ = "ingested_posting_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[str] = mapped_column(String(64), ForeignKey("import_batches.batch_id"), nullable=False, index=True)
    posting_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_title: Mapped[str] = mapped_column(String(255), nullable=False)
    district_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    observation_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vacancy_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    batch: Mapped["ImportBatch"] = relationship("ImportBatch", back_populates="records")
