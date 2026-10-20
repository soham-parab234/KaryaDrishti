"""Pydantic schemas for NCO-2015 reference data, title normalization, and human review."""

from pydantic import BaseModel, Field

class NcoOccupationItem(BaseModel):
    nco_code: str = Field(..., description="NCO-2015 4-digit or 8-digit code (e.g. 7421.0301)")
    canonical_title: str
    division_code: str
    division_title: str
    sub_major_code: str | None = None
    sub_major_title: str | None = None
    minor_code: str | None = None
    minor_title: str | None = None
    unit_group_code: str | None = None
    unit_group_title: str | None = None
    description: str | None = None
    source_status: str = Field("PILOT_BASELINE", description="'OFFICIAL_DGE', 'PILOT_BASELINE', or 'SYNTHETIC_DEMO'")
    is_verified: bool = True
    aliases: list[str] = Field(default_factory=list)

class NcoReferenceListResponse(BaseModel):
    total: int
    items: list[NcoOccupationItem]

class ReferenceImportSummary(BaseModel):
    filename: str
    source_status: str
    occupations_imported: int
    aliases_imported: int
    message: str

class CandidateMatchItem(BaseModel):
    nco_code: str
    canonical_title: str
    matched_alias: str | None = None
    match_method: str
    confidence: float
    rationale: str

class NormalizeTitleRequest(BaseModel):
    raw_title: str = Field(..., min_length=1, max_length=255, description="Raw job title to clean and normalize")
    source_system: str | None = Field("MANUAL_INPUT", description="Source channel name")

class NormalizeTitleResponse(BaseModel):
    raw_title: str
    normalized_title: str
    status: str = Field(..., description="'UNMATCHED', 'PROPOSED', or 'APPROVED'")
    match_method: str = Field(..., description="'EXACT_CANONICAL', 'EXACT_ALIAS', 'TOKEN_OVERLAP', or 'NONE'")
    confidence: float = Field(..., description="Confidence score from 0.0 to 100.0")
    proposed_nco_code: str | None = None
    proposed_canonical_title: str | None = None
    match_rationale: str
    candidate_matches: list[CandidateMatchItem] = Field(default_factory=list)

class ReviewProposalItem(BaseModel):
    id: int
    raw_title: str
    normalized_title: str
    source_system: str
    batch_id: str | None = None
    posting_record_id: int | None = None
    proposed_nco_code: str | None = None
    proposed_canonical_title: str | None = None
    match_method: str
    confidence: float
    match_rationale: str
    status: str
    reviewer_decision: str | None = None
    reviewer_note: str | None = None
    reviewed_at: str | None = None
    created_at: str

class ProposalReviewRequest(BaseModel):
    decision: str = Field(..., description="'APPROVED', 'REJECTED', or 'OVERRIDDEN'")
    override_nco_code: str | None = Field(None, description="Optional override NCO code if reviewer selects a different taxonomy code")
    reviewer_note: str | None = Field(None, description="Auditable reviewer explanation or rationale")

class ProposalReviewResponse(BaseModel):
    id: int
    status: str
    reviewer_decision: str
    assigned_nco_code: str | None = None
    canonical_title: str | None = None
    reviewed_at: str
    message: str

class BatchNormalizationResponse(BaseModel):
    batch_id: str
    total_postings_processed: int
    proposals_created: int
    unmatched_count: int
    proposed_count: int
    message: str
