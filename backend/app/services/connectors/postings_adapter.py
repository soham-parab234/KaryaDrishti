"""Job Postings CSV Adapter (Phase 11: Data Integration Readiness).

Reusable, validated adapter for importing employer vacancy announcements
from NCS exports, job portal feeds, and enterprise labor surveys.
"""

from typing import Any
from sqlalchemy.orm import Session
from backend.app.services.connectors.base import BaseDataConnector, ConnectorMetadata
from backend.app.services.csv_validator import validate_csv_content
from backend.app.models.ingestion import ImportBatch, IngestedPostingRecord


class PostingsCsvAdapter(BaseDataConnector):
    """Adapter for canonical job postings CSV format."""

    def get_metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="POSTINGS_CSV_ADAPTER",
            connector_name="Employer Job Postings CSV Adapter",
            source_family="JOB_POSTINGS",
            connection_status="ACTIVE_LOCAL_ADAPTER",
            auth_mechanism="NONE_FILE_UPLOAD",
            is_live_connection=False,
            expected_schema={
                "posting_id": "string (unique identifier)",
                "raw_title": "string (3-150 characters)",
                "district_code": "string (e.g. MH_PUN, MH_NSK)",
                "observation_date": "date (YYYY-MM-DD)",
                "source_system": "string (NCS_FEED, PORTAL_SCRAPE, SCHEME_MIS, ENTERPRISE_SURVEY)",
                "vacancy_count": "integer (>= 1, optional)",
            },
            description="Validates and ingests employer job postings batches into the normalization review queue.",
            limitations_notice="Job postings represent raw hiring intent signals, not verified economic employment. Unapproved postings are excluded from confirmed demand until reviewed.",
            verification_disclaimer="Imported postings are labeled 'IMPORTED' and must pass title mapping review before entering demand analytics.",
        )

    def validate_input(self, content: bytes, filename: str = "upload.csv") -> dict[str, Any]:
        res = validate_csv_content(content, filename=filename)
        return {
            "is_valid": res.is_valid,
            "status": res.status,
            "filename": res.filename,
            "file_size_bytes": res.file_size_bytes,
            "file_hash": res.file_hash,
            "total_rows": res.total_rows,
            "valid_rows": res.valid_rows,
            "rejected_rows": res.rejected_rows,
            "errors": [e.model_dump() if hasattr(e, "model_dump") else e.__dict__ for e in res.errors],
            "message": res.message,
        }

    def import_data(
        self,
        content: bytes,
        db: Session,
        filename: str = "upload.csv",
        batch_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        val = validate_csv_content(content, filename=filename)
        if not val.is_valid:
            raise ValueError(f"CSV validation failed: {val.message}")

        import uuid
        bid = batch_id or f"batch-{uuid.uuid4().hex[:12]}"

        # Check duplicate file hash
        existing = db.query(ImportBatch).filter(ImportBatch.file_hash == val.file_hash).first()
        if existing:
            raise ValueError(f"Duplicate batch submission: File with identical SHA-256 hash was previously ingested as batch {existing.batch_id}.")

        batch = ImportBatch(
            batch_id=bid,
            filename=val.filename,
            file_hash=val.file_hash,
            total_rows=val.total_rows,
            valid_rows=val.valid_rows,
            rejected_rows=0,
            status="COMPLETED",
        )
        db.add(batch)

        for rec in val.valid_records:
            posting = IngestedPostingRecord(
                batch_id=bid,
                posting_id=rec.posting_id,
                raw_title=rec.raw_title,
                district_code=rec.district_code,
                observation_date=rec.observation_date,
                source_system=rec.source_system,
                vacancy_count=rec.vacancy_count,
            )
            db.add(posting)

        db.commit()

        return {
            "batch_id": bid,
            "filename": val.filename,
            "total_rows": val.total_rows,
            "valid_rows": val.valid_rows,
            "status": "COMPLETED",
            "message": f"Successfully ingested {val.valid_rows} job posting record(s) into batch {bid}.",
        }
