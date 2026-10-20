"""Health check endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.schemas.health import HealthResponse
from backend.app.db.session import get_db

router = APIRouter(prefix="", tags=["System"])

@router.get("/health", response_model=HealthResponse, summary="System & Database Health Check")
def get_system_health(db: Session = Depends(get_db)) -> HealthResponse:
    """Evaluate API runtime status and database connectivity."""
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        database="connected" if db_connected else "disconnected",
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment="development",
    )
