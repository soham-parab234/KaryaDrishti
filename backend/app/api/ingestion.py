"""CSV ingestion endpoints for validation, persistence, and batch auditing."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.ingestion import ImportBatch, IngestedPostingRecord
from backend.app.schemas.ingestion import (
    ValidationSummaryResponse,
    ImportResponse,
    ImportBatchSummary,
)
from backend.app.services.csv_validator import validate_csv_content

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion"])

@router.post(
    "/validate",
    response_model=ValidationSummaryResponse,
    summary="Validate CSV file against canonical schema without persisting",
)
async def validate_csv(
    file: UploadFile = File(..., description="CSV file to validate against canonical LMIS schema"),
) -> ValidationSummaryResponse:
    """Validate uploaded CSV structure, required headers, row fields, and constraint rules."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CSV file provided in the upload request.",
        )

    # Read uploaded bytes
    content = await file.read()

    result = validate_csv_content(content, filename=file.filename)

    return ValidationSummaryResponse(
        status=result.status,
        filename=result.filename,
        file_size_bytes=result.file_size_bytes,
        total_rows=result.total_rows,
        valid_rows=result.valid_rows,
        rejected_rows=result.rejected_rows,
        errors=result.errors,
        sample_valid_records=result.valid_records[:5],
        schema_version="1.0",
        message=result.message,
    )

@router.post(
    "/import",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Validate and persist clean CSV records into database",
)
async def import_csv_batch(
    file: UploadFile = File(..., description="CSV file containing valid job postings"),
    db: Session = Depends(get_db),
) -> ImportResponse:
    """Validate and persist an entire CSV batch.

    Strict Data Integrity Rules:
    - Never silently accepts invalid records.
    - If ANY row fails validation, the entire batch is rejected (zero partial writes).
    - Checks for duplicate batch submissions using SHA-256 file hash.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CSV file provided for ingestion import.",
        )

    content = await file.read()
    result = validate_csv_content(content, filename=file.filename)

    # 1. Reject if validation failed
    if not result.is_valid:
        error_preview = [e.model_dump() for e in result.errors[:10]]
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail={
                "error": "Batch validation failed. No records were imported.",
                "total_rows": result.total_rows,
                "rejected_rows": result.rejected_rows,
                "errors_preview": error_preview,
                "message": result.message,
            },
        )

    # 2. Duplicate batch detection via file_hash
    existing_batch = db.query(ImportBatch).filter(ImportBatch.file_hash == result.file_hash).first()
    if existing_batch:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Duplicate batch detected. This identical file content was previously imported on "
                f"{existing_batch.uploaded_at.isoformat()} as batch '{existing_batch.batch_id}'."
            ),
        )

    # 3. Create and persist batch record
    now = datetime.now(timezone.utc)
    batch_id = f"BATCH-{now.strftime('%Y-%m')}-{uuid.uuid4().hex[:6].upper()}"

    batch = ImportBatch(
        batch_id=batch_id,
        filename=file.filename,
        file_hash=result.file_hash,
        uploaded_at=now,
        total_rows=result.total_rows,
        valid_rows=result.valid_rows,
        rejected_rows=0,
        status="COMPLETED",
        error_summary=None,
    )
    db.add(batch)

    # 4. Insert posting records
    records = [
        IngestedPostingRecord(
            batch_id=batch_id,
            posting_id=item.posting_id,
            raw_title=item.raw_title,
            district_code=item.district_code,
            observation_date=item.observation_date,
            source_system=item.source_system,
            vacancy_count=item.vacancy_count,
            created_at=now,
        )
        for item in result.valid_records
    ]
    db.add_all(records)
    db.commit()

    from backend.app.services.audit_service import record_audit_event
    record_audit_event(
        db=db,
        event_type="INGESTION_BATCH_IMPORT",
        entity_type="BATCH",
        entity_id=batch_id,
        action_summary=f"Ingested batch {batch_id} with {len(records)} verified vacancy records from {file.filename}",
        actor="API_UPLOADER",
        details={"filename": file.filename, "file_hash": result.file_hash, "imported_rows": len(records)},
    )

    return ImportResponse(
        batch_id=batch_id,
        filename=file.filename,
        status="COMPLETED",
        uploaded_at=now.isoformat(),
        total_rows=result.total_rows,
        imported_rows=len(records),
        rejected_rows=0,
        file_hash=result.file_hash,
        proposals_created=0,
        message=f"Successfully imported {len(records)} verified records under batch '{batch_id}'.",
    )

@router.get(
    "/batches",
    response_model=list[ImportBatchSummary],
    summary="List audit history of imported batches",
)
def list_import_batches(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[ImportBatchSummary]:
    """Retrieve audit ledger of previously ingested batches."""
    batches = (
        db.query(ImportBatch)
        .order_by(ImportBatch.uploaded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        ImportBatchSummary(
            batch_id=b.batch_id,
            filename=b.filename,
            uploaded_at=b.uploaded_at.isoformat(),
            total_rows=b.total_rows,
            valid_rows=b.valid_rows,
            rejected_rows=b.rejected_rows,
            status=b.status,
            error_summary=b.error_summary,
        )
        for b in batches
    ]


@router.get(
    "/connectors",
    summary="List all data source connectors, adapters, and planned integrations (Phase 11)",
)
def get_connectors():
    """Retrieve metadata for all supported adapters and planned national integrations."""
    from backend.app.services.connectors import list_all_connectors
    return list_all_connectors()


@router.post(
    "/validate-supply",
    summary="Validate institutional training capacity CSV without persisting",
)
async def validate_training_supply_csv(
    file: UploadFile = File(..., description="Training capacity CSV file"),
):
    """Validate institutional training capacity and graduate outcomes structure."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CSV file provided in the upload request.",
        )
    from backend.app.services.connectors import TrainingSupplyCsvAdapter
    content = await file.read()
    adapter = TrainingSupplyCsvAdapter()
    return adapter.validate_input(content, filename=file.filename)


@router.post(
    "/import-supply",
    status_code=status.HTTP_201_CREATED,
    summary="Validate and persist clean training capacity CSV records (Phase 11)",
)
async def import_training_supply_csv(
    file: UploadFile = File(..., description="Training capacity CSV file"),
    db: Session = Depends(get_db),
):
    """Validate and atomically persist institutional training capacity records."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CSV file provided in the upload request.",
        )
    from backend.app.services.connectors import TrainingSupplyCsvAdapter
    content = await file.read()
    adapter = TrainingSupplyCsvAdapter()
    try:
        res = adapter.import_data(content, db=db, filename=file.filename)
        from backend.app.services.audit_service import record_audit_event
        record_audit_event(
            db=db,
            event_type="TRAINING_SUPPLY_IMPORT",
            entity_type="SUPPLY",
            entity_id=file.filename,
            action_summary=f"Ingested {res['records_persisted']} institutional training capacity record(s) from {file.filename}",
            actor="API_UPLOADER",
            details=res,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

