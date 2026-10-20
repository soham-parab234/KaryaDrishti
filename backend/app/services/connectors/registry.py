"""Connector Registry and Metadata Provider (Phase 11: Data Integration Readiness)."""

from backend.app.services.connectors.base import BaseDataConnector, ConnectorMetadata
from backend.app.services.connectors.postings_adapter import PostingsCsvAdapter
from backend.app.services.connectors.supply_adapter import TrainingSupplyCsvAdapter
from backend.app.services.connectors.planned_connectors import (
    NcsApiConnector,
    EShramApiConnector,
    NcvetSipConnector,
)

_REGISTRY: dict[str, BaseDataConnector] = {
    "POSTINGS_CSV_ADAPTER": PostingsCsvAdapter(),
    "TRAINING_SUPPLY_CSV_ADAPTER": TrainingSupplyCsvAdapter(),
    "NCS_API_CONNECTOR": NcsApiConnector(),
    "ESHRAM_API_CONNECTOR": EShramApiConnector(),
    "NCVET_SIP_CONNECTOR": NcvetSipConnector(),
}


def get_connector(connector_id: str) -> BaseDataConnector | None:
    """Retrieve connector instance by machine identifier."""
    return _REGISTRY.get(connector_id)


def get_connector_registry() -> dict[str, BaseDataConnector]:
    """Retrieve mapping of all registered connectors."""
    return _REGISTRY


def list_all_connectors() -> list[ConnectorMetadata]:
    """List metadata for all active adapters and planned integrations."""
    return [conn.get_metadata() for conn in _REGISTRY.values()]
