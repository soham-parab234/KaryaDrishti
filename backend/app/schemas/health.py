"""Pydantic schemas for health endpoint."""

from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status (e.g. 'healthy', 'degraded')")
    database: str = Field(..., description="Database connectivity status (e.g. 'connected', 'disconnected')")
    version: str = Field(..., description="API software version")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of health evaluation")
    environment: str = Field("development", description="Runtime environment indicator")
