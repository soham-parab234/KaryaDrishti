"""LMIS Forecasting Engine — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.db.session import init_db, SessionLocal
from backend.app.services.nco_reference import seed_pilot_baseline_nco
from backend.app.services.analytics_service import seed_pilot_baseline_analytics
from backend.app.services.forecasting import seed_demo_time_series
from backend.app.services.alerts_service import evaluate_and_generate_alerts
from backend.app.services.recommendations_service import generate_policy_recommendations
from backend.app.api.health import router as health_router
from backend.app.api.ingestion import router as ingestion_router
from backend.app.api.occupations import router as occupations_router
from backend.app.api.normalization import router as normalization_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.forecasting import router as forecasting_router
from backend.app.api.alerts import router as alerts_router
from backend.app.api.scenarios import router as scenarios_router
from backend.app.api.recommendations import router as recommendations_router
from backend.app.api.governance import router as governance_router
from backend.app.api.ai import router as ai_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    # Initialize SQLite database tables
    init_db()

    # Seed baseline NCO taxonomy, analytics, demonstration time-series, alerts, and recommendations
    with SessionLocal() as db:
        seed_pilot_baseline_nco(db)
        seed_pilot_baseline_analytics(db)
        seed_demo_time_series(db)
        evaluate_and_generate_alerts(db)
        generate_policy_recommendations(db)

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "https://lmis-forecasting-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under /api
app.include_router(health_router, prefix=settings.API_PREFIX)
app.include_router(ingestion_router, prefix=settings.API_PREFIX)
app.include_router(occupations_router, prefix=settings.API_PREFIX)
app.include_router(normalization_router, prefix=settings.API_PREFIX)
app.include_router(analytics_router, prefix=settings.API_PREFIX)
app.include_router(forecasting_router, prefix=settings.API_PREFIX)
app.include_router(alerts_router, prefix=settings.API_PREFIX)
app.include_router(scenarios_router, prefix=settings.API_PREFIX)
app.include_router(recommendations_router, prefix=settings.API_PREFIX)
app.include_router(governance_router, prefix=settings.API_PREFIX)
app.include_router(ai_router, prefix=settings.API_PREFIX)



@app.get("/", tags=["System"])
def root_summary():
    """Root metadata response directing to OpenAPI interactive documentation."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs",
        "health_endpoint": f"{settings.API_PREFIX}/health",
        "ingestion_validate_endpoint": f"{settings.API_PREFIX}/ingestion/validate",
        "ingestion_import_endpoint": f"{settings.API_PREFIX}/ingestion/import",
        "reference_occupations_endpoint": f"{settings.API_PREFIX}/occupations/reference",
        "normalization_normalize_endpoint": f"{settings.API_PREFIX}/normalization/normalize",
        "normalization_proposals_endpoint": f"{settings.API_PREFIX}/normalization/proposals",
        "analytics_gaps_endpoint": f"{settings.API_PREFIX}/analytics/gaps",
        "analytics_gap_detail_endpoint": f"{settings.API_PREFIX}/analytics/gaps/detail",
    }
