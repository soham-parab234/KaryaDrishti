"""LMIS Labour Market Intelligence AI Assistant API Route.

Provides POST /api/ai/ask for grounded natural-language queries.
Strictly read-only; answers are synthesized from SQLite analytical models.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.ai import AiQueryRequest, AiQueryResponse
from backend.app.services.ai_assistant import process_ai_query
from backend.app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post(
    "/ask",
    response_model=AiQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the AI Labour Market Intelligence Assistant",
    description=(
        "Processes an analytical query using grounded LMIS records. "
        "Uses Google Gemini if configured, or falls back gracefully to deterministic rule-based intelligence. "
        "Read-only: cannot alter database records or approve job postings."
    ),
)
async def ask_ai_assistant(
    request: AiQueryRequest,
    db: Session = Depends(get_db),
) -> AiQueryResponse:
    """Execute grounded intelligence analysis."""
    clean_query = request.query.strip()
    if len(clean_query) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must contain at least 2 non-whitespace characters.",
        )

    try:
        response = await process_ai_query(db=db, request=request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Internal failure processing AI query: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal intelligence engine error: Unable to retrieve or evaluate grounded database evidence.",
        )

    # Record tamper-evident read-only query audit event
    try:
        record_audit_event(
            db=db,
            event_type="AI_ASSISTANT_QUERY",
            entity_type="ANALYTICS_QUERY",
            entity_id=request.district_code or "ALL_DISTRICTS",
            action_summary=f"AI query processed in {response.mode} mode ({response.status})",
            actor="PLANNING_OFFICER",
            details={
                "query": clean_query[:100],
                "mode": response.mode,
                "provider": response.provider,
                "status": response.status,
                "evidence_count": len(response.evidence),
            },
        )
    except Exception as exc:
        logger.warning("Audit event recording failed for AI query: %s", type(exc).__name__)

    return response
