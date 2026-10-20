"""Automated tests for health and root endpoints."""

from fastapi.testclient import TestClient

def test_api_health_endpoint(client: TestClient):
    """GET /api/health should return status 'healthy' and database 'connected'."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data

def test_root_endpoint(client: TestClient):
    """GET / should return service metadata and endpoint links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "health_endpoint" in data
    assert "docs_url" in data
