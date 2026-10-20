"""Pydantic schemas package."""

from backend.app.schemas.health import HealthResponse
from backend.app.schemas.ingestion import (
    RowValidationError,
    ValidationSummaryResponse,
    ImportResponse,
    ImportBatchSummary,
)
from backend.app.schemas.occupation import (
    NcoOccupationItem,
    NcoReferenceListResponse,
    ReferenceImportSummary,
    NormalizeTitleRequest,
    NormalizeTitleResponse,
    CandidateMatchItem,
    ReviewProposalItem,
    ProposalReviewRequest,
    ProposalReviewResponse,
    BatchNormalizationResponse,
)
from backend.app.schemas.analytics import (
    DemandObservationCreate,
    DemandObservationItem,
    QualifiedSupplyEstimateCreate,
    QualifiedSupplyEstimateItem,
    TrainingCapacityCreate,
    TrainingCapacityItem,
    GapIndicatorSummary,
    GapDetailAuditResponse,
    DemandAggregationResponse,
)

from backend.app.schemas.ai import (
    AiEvidenceItem,
    AiQueryRequest,
    AiQueryResponse,
)

__all__ = [
    "HealthResponse",
    "RowValidationError",
    "ValidationSummaryResponse",
    "ImportResponse",
    "ImportBatchSummary",
    "NcoOccupationItem",
    "NcoReferenceListResponse",
    "ReferenceImportSummary",
    "NormalizeTitleRequest",
    "NormalizeTitleResponse",
    "CandidateMatchItem",
    "ReviewProposalItem",
    "ProposalReviewRequest",
    "ProposalReviewResponse",
    "BatchNormalizationResponse",
    "DemandObservationCreate",
    "DemandObservationItem",
    "QualifiedSupplyEstimateCreate",
    "QualifiedSupplyEstimateItem",
    "TrainingCapacityCreate",
    "TrainingCapacityItem",
    "GapIndicatorSummary",
    "GapDetailAuditResponse",
    "DemandAggregationResponse",
    "AiEvidenceItem",
    "AiQueryRequest",
    "AiQueryResponse",
]
