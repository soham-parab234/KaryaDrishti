"""Base connector interfaces for LMIS data ingestion (Phase 11: Data Integration Readiness).

Ensures clear modular boundaries between data formats, validation rules,
and storage targets, while strictly forbidding unauthorized claims of live
government connectivity without working verified credentials.
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class ConnectorMetadata(BaseModel):
    """Metadata describing a data source connector, its security requirements, and provenance."""

    connector_id: str = Field(..., description="Unique machine identifier for connector")
    connector_name: str = Field(..., description="Human-readable title of data connector")
    source_family: str = Field(
        ...,
        description="Data domain: JOB_POSTINGS, QUALIFIED_SUPPLY, TRAINING_CAPACITY, WORKER_REGISTRATIONS"
    )
    connection_status: str = Field(
        ...,
        description="Integration status: ACTIVE_LOCAL_ADAPTER, PLANNED_GOVERNMENT_INTEGRATION, DISABLED"
    )
    auth_mechanism: str = Field(
        "NONE_FILE_UPLOAD",
        description="Authentication type: NONE_FILE_UPLOAD, API_KEY_ENV, OAUTH2_PLANNED, MUTUAL_TLS_PLANNED"
    )
    is_live_connection: bool = Field(
        False,
        description="Whether a verified live API integration is active. False if mock or file-based."
    )
    expected_schema: dict[str, str] = Field(..., description="Dictionary of expected field names and data types")
    description: str = Field(..., description="Description of the data connector")
    limitations_notice: str = Field(..., description="Known operational limitations and data caveats")
    verification_disclaimer: str = Field(
        "Data ingested via this connector must be validated and human-approved before contributing to official analytics.",
        description="Governance policy disclaimer"
    )


class BaseDataConnector(ABC):
    """Abstract base class for all LMIS data ingestion connectors."""

    @abstractmethod
    def get_metadata(self) -> ConnectorMetadata:
        """Return the connector's metadata, status, and schema definition."""
        pass

    @abstractmethod
    def validate_input(self, content: bytes, filename: str = "upload.csv") -> dict[str, Any]:
        """Validate the incoming payload against connector schema rules."""
        pass

    @abstractmethod
    def import_data(self, content: bytes, db: Session, filename: str = "upload.csv", **kwargs) -> dict[str, Any]:
        """Validate and atomically persist clean records into target tables."""
        pass
