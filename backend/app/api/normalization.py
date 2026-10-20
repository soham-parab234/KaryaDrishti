"""Title Normalization & Human-in-the-Loop Review Queue API Endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.ingestion import ImportBatch, IngestedPostingRecord
from backend.app.models.occupation import NcoOccupation, OccupationAlias, TitleMappingReview
from backend.app.schemas.occupation import (
    NormalizeTitleRequest,
    NormalizeTitleResponse,
    ReviewProposalItem,
    ProposalReviewRequest,
    ProposalReviewResponse,
    BatchNormalizationResponse,
)
from backend.app.services.normalization import match_job_title, clean_title
from backend.app.services.nco_reference import normalize_string_key

router = APIRouter(prefix="/normalization", tags=["Occupation Normalization & Review"])

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@router.post(
    "/normalize",
    response_model=NormalizeTitleResponse,
    summary="Evaluate title normalization and candidate matches in-memory",
)
def evaluate_normalization(
    payload: NormalizeTitleRequest,
    db: Session = Depends(get_db),
) -> NormalizeTitleResponse:
    """Clean and normalize a raw title and evaluate proposed NCO taxonomy matches."""
    result = match_job_title(payload.raw_title, db)
    return NormalizeTitleResponse(
        raw_title=result.raw_title,
        normalized_title=result.normalized_title,
        status=result.status,
        match_method=result.match_method,
        confidence=result.confidence,
        proposed_nco_code=result.proposed_nco_code,
        proposed_canonical_title=result.proposed_canonical_title,
        match_rationale=result.match_rationale,
        candidate_matches=result.candidates,
    )

@router.post(
    "/process-batch/{batch_id}",
    response_model=BatchNormalizationResponse,
    summary="Normalize all posting records in an imported batch",
)
def process_batch_normalization(
    batch_id: str,
    db: Session = Depends(get_db),
) -> BatchNormalizationResponse:
    """Connect ingested posting records to title normalization and review queue."""
    batch = db.query(ImportBatch).filter(ImportBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import batch '{batch_id}' not found.",
        )

    postings = (
        db.query(IngestedPostingRecord)
        .filter(IngestedPostingRecord.batch_id == batch_id)
        .all()
    )

    if not postings:
        return BatchNormalizationResponse(
            batch_id=batch_id,
            total_postings_processed=0,
            proposals_created=0,
            unmatched_count=0,
            proposed_count=0,
            message=f"Batch '{batch_id}' contains no ingested postings to process.",
        )

    proposals_created = 0
    unmatched_count = 0
    proposed_count = 0

    for posting in postings:
        # Check if already processed
        existing = (
            db.query(TitleMappingReview)
            .filter(TitleMappingReview.posting_record_id == posting.id)
            .first()
        )
        if existing:
            continue

        result = match_job_title(posting.raw_title, db)

        review = TitleMappingReview(
            posting_record_id=posting.id,
            batch_id=batch_id,
            raw_title=posting.raw_title,
            normalized_title=result.normalized_title,
            source_system=posting.source_system,
            proposed_nco_code=result.proposed_nco_code,
            proposed_canonical_title=result.proposed_canonical_title,
            match_method=result.match_method,
            confidence=result.confidence,
            match_rationale=result.match_rationale,
            status=result.status,
            reviewer_decision=None,
            reviewer_note=None,
            reviewed_at=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(review)
        proposals_created += 1

        if result.status == "UNMATCHED":
            unmatched_count += 1
        else:
            proposed_count += 1

    db.commit()

    return BatchNormalizationResponse(
        batch_id=batch_id,
        total_postings_processed=len(postings),
        proposals_created=proposals_created,
        unmatched_count=unmatched_count,
        proposed_count=proposed_count,
        message=f"Batch normalization completed: {proposals_created} review items created ({proposed_count} proposed, {unmatched_count} unmatched).",
    )

@router.get(
    "/proposals",
    response_model=list[ReviewProposalItem],
    summary="List normalization review proposals",
)
def list_review_proposals(
    review_status: str | None = Query(None, description="Filter by status: 'PROPOSED', 'UNMATCHED', 'APPROVED', 'REJECTED'"),
    batch_id: str | None = Query(None, description="Filter by import batch ID"),
    source_system: str | None = Query(None, description="Filter by source portal/channel"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[ReviewProposalItem]:
    """Retrieve unresolved or reviewed occupation mapping proposals."""
    query = db.query(TitleMappingReview)

    if review_status:
        query = query.filter(TitleMappingReview.status == review_status.upper())

    if batch_id:
        query = query.filter(TitleMappingReview.batch_id == batch_id)

    if source_system:
        query = query.filter(TitleMappingReview.source_system == source_system)

    reviews = (
        query.order_by(TitleMappingReview.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        ReviewProposalItem(
            id=r.id,
            raw_title=r.raw_title,
            normalized_title=r.normalized_title,
            source_system=r.source_system,
            batch_id=r.batch_id,
            posting_record_id=r.posting_record_id,
            proposed_nco_code=r.proposed_nco_code,
            proposed_canonical_title=r.proposed_canonical_title,
            match_method=r.match_method,
            confidence=r.confidence,
            match_rationale=r.match_rationale,
            status=r.status,
            reviewer_decision=r.reviewer_decision,
            reviewer_note=r.reviewer_note,
            reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
            created_at=r.created_at.isoformat(),
        )
        for r in reviews
    ]

@router.get(
    "/proposals/{proposal_id}",
    response_model=ReviewProposalItem,
    summary="Get single review proposal details",
)
def get_review_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
) -> ReviewProposalItem:
    """Retrieve a single mapping review item by ID."""
    review = db.query(TitleMappingReview).filter(TitleMappingReview.id == proposal_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review proposal with ID {proposal_id} not found.",
        )

    return ReviewProposalItem(
        id=review.id,
        raw_title=review.raw_title,
        normalized_title=review.normalized_title,
        source_system=review.source_system,
        batch_id=review.batch_id,
        posting_record_id=review.posting_record_id,
        proposed_nco_code=review.proposed_nco_code,
        proposed_canonical_title=review.proposed_canonical_title,
        match_method=review.match_method,
        confidence=review.confidence,
        match_rationale=review.match_rationale,
        status=review.status,
        reviewer_decision=review.reviewer_decision,
        reviewer_note=review.reviewer_note,
        reviewed_at=review.reviewed_at.isoformat() if review.reviewed_at else None,
        created_at=review.created_at.isoformat(),
    )

@router.post(
    "/proposals/{proposal_id}/review",
    response_model=ProposalReviewResponse,
    summary="Record human reviewer decision on a mapping proposal",
)
def record_proposal_review(
    proposal_id: int,
    payload: ProposalReviewRequest,
    db: Session = Depends(get_db),
) -> ProposalReviewResponse:
    """Submit human reviewer decision to approve, reject, or override a title mapping.

    Audit & Integrity Controls:
    - Target NCO codes are strictly validated against loaded NCO reference taxonomy.
    - An approved mapping is persistently recorded with timestamp.
    - If approved, the verified title is learned as an alias for future exact matching.
    """
    review = db.query(TitleMappingReview).filter(TitleMappingReview.id == proposal_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review proposal with ID {proposal_id} not found.",
        )

    decision = payload.decision.upper()
    if decision not in ("APPROVED", "REJECTED", "OVERRIDDEN"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review decision must be one of 'APPROVED', 'REJECTED', or 'OVERRIDDEN'.",
        )

    target_nco_code = review.proposed_nco_code

    if decision in ("APPROVED", "OVERRIDDEN"):
        if payload.override_nco_code:
            target_nco_code = payload.override_nco_code.strip()

        if not target_nco_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve proposal without a valid NCO code. Please specify an override NCO code.",
            )

        # Validate that target NCO code exists in authoritative reference store
        occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == target_nco_code).first()
        if not occ:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve: NCO code '{target_nco_code}' does not exist in the loaded reference taxonomy.",
            )

        review.proposed_nco_code = occ.nco_code
        review.proposed_canonical_title = occ.canonical_title
        review.status = "APPROVED"
        review.reviewer_decision = decision
        review.reviewer_note = payload.reviewer_note
        review.reviewed_at = utc_now()
        review.updated_at = utc_now()

        # Learn the raw title as a verified alias for exact matching in future batches
        norm_key = normalize_string_key(review.raw_title)
        existing_alias = (
            db.query(OccupationAlias)
            .filter(
                OccupationAlias.nco_code == occ.nco_code,
                OccupationAlias.alias_normalized == norm_key,
            )
            .first()
        )
        if not existing_alias:
            db.add(
                OccupationAlias(
                    nco_code=occ.nco_code,
                    alias_raw=review.raw_title,
                    alias_normalized=norm_key,
                    source="REVIEWER_APPROVED",
                    is_verified=True,
                )
            )

        db.commit()

        from backend.app.services.audit_service import record_audit_event
        record_audit_event(
            db=db,
            event_type="OCCUPATION_MAPPING_REVIEW",
            entity_type="OCCUPATION_REVIEW",
            entity_id=str(proposal_id),
            action_summary=f"Approved mapping for '{review.raw_title}' -> NCO {occ.nco_code} ({occ.canonical_title})",
            actor="HUMAN_REVIEWER",
            details={"proposal_id": proposal_id, "raw_title": review.raw_title, "nco_code": occ.nco_code, "decision": decision},
        )

        return ProposalReviewResponse(
            id=review.id,
            status="APPROVED",
            reviewer_decision=decision,
            assigned_nco_code=occ.nco_code,
            canonical_title=occ.canonical_title,
            reviewed_at=review.reviewed_at.isoformat(),
            message=f"Proposal {proposal_id} approved. Mapped to NCO {occ.nco_code} ({occ.canonical_title}).",
        )

    else:  # REJECTED
        review.status = "REJECTED"
        review.reviewer_decision = "REJECTED"
        review.reviewer_note = payload.reviewer_note
        review.reviewed_at = utc_now()
        review.updated_at = utc_now()

        db.commit()

        from backend.app.services.audit_service import record_audit_event
        record_audit_event(
            db=db,
            event_type="OCCUPATION_MAPPING_REVIEW",
            entity_type="OCCUPATION_REVIEW",
            entity_id=str(proposal_id),
            action_summary=f"Rejected mapping for '{review.raw_title}'",
            actor="HUMAN_REVIEWER",
            details={"proposal_id": proposal_id, "raw_title": review.raw_title, "decision": "REJECTED", "notes": payload.reviewer_note},
        )

        return ProposalReviewResponse(
            id=review.id,
            status="REJECTED",
            reviewer_decision="REJECTED",
            assigned_nco_code=review.proposed_nco_code,
            canonical_title=review.proposed_canonical_title,
            reviewed_at=review.reviewed_at.isoformat(),
            message=f"Proposal {proposal_id} marked as REJECTED.",
        )
