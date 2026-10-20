"""Data Integration Connectors and Adapters Package (Phase 11: Data Integration Readiness)."""

from backend.app.services.connectors.base import BaseDataConnector, ConnectorMetadata
from backend.app.services.connectors.postings_adapter import PostingsCsvAdapter
from backend.app.services.connectors.supply_adapter import TrainingSupplyCsvAdapter
from backend.app.services.connectors.registry import get_connector_registry, list_all_connectors

__all__ = [
    "BaseDataConnector",
    "ConnectorMetadata",
    "PostingsCsvAdapter",
    "TrainingSupplyCsvAdapter",
    "get_connector_registry",
    "list_all_connectors",
]
