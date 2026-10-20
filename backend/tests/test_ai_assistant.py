"""Tests for LMIS Labour Market Intelligence AI Assistant.

Verifies:
1. Grounded response generation using database models.
2. Graceful deterministic rule-based fallback when GEMINI_API_KEY is unset.
3. Live Gemini provider integration handling via mock.
4. Provider error handling (HTTP 403, timeout) with graceful fallback.
5. Input validation (whitespace, short queries).
6. Insufficient data states.
7. Read-only guarantee (no mutation of business records).
8. Audit event generation.
"""

import pytest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.models.analytics import DemandObservation, QualifiedSupplyEstimate
from backend.app.models.audit import AuditEvent


def test_ai_ask_valid_query_rule_based_fallback(client: TestClient, db_session: Session):
    """Test AI endpoint when no API key is configured; should use rule-based fallback."""
    with patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post(
            "/api/ai/ask",
            json={"query": "What are the top skill shortages in Pune district?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "RULE_BASED_FALLBACK"
        assert "Deterministic Rule-Based" in data["provider"]
        assert data["status"] == "SUCCESS"
        assert len(data["evidence"]) > 0
        assert len(data["limitations"]) > 0
        assert "Maharashtra Pilot Baseline" in data["disclaimer"]

        # Verify specific grounded occupational evidence for Pune
        pune_evidence = [e for e in data["evidence"] if e["district_code"] == "MH_PUN"]
        assert len(pune_evidence) > 0

        # Verify an AI_ASSISTANT_QUERY audit event was logged
        audit_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.event_type == "AI_ASSISTANT_QUERY")
            .order_by(AuditEvent.id.desc())
            .first()
        )
        assert audit_event is not None
        assert "AI query processed" in audit_event.action_summary


def test_ai_ask_specific_occupation_grounding(client: TestClient):
    """Test AI endpoint for specific occupation keywords and district filtering."""
    with patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post(
            "/api/ai/ask",
            json={
                "query": "What is the demand and supply gap for Solar PV Technician?",
                "district_code": "MH_PUN",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"

        # Evidence should contain Solar PV Technician (7421.0301)
        solar_items = [e for e in data["evidence"] if e["nco_code"] == "7421.0301"]
        assert len(solar_items) > 0
        solar = solar_items[0]
        assert solar["canonical_title"] == "Solar PV Installation & Maintenance Technician"
        assert solar["demand_value"] == 680.0
        assert solar["supply_value"] == 420.0
        assert solar["absolute_gap"] == 260.0
        assert solar["risk_level"] == "CRITICAL_SHORTAGE"


def test_ai_ask_invalid_input_validation(client: TestClient):
    """Test input validation for blank or whitespace-only queries."""
    # Blank query
    resp1 = client.post("/api/ai/ask", json={"query": "   "})
    assert resp1.status_code == 400
    assert "Query must contain at least 2 non-whitespace characters" in resp1.json()["detail"]

    # Too short query (< 2 characters)
    resp2 = client.post("/api/ai/ask", json={"query": "a"})
    assert resp2.status_code in (400, 422)


def test_ai_ask_insufficient_data_state(client: TestClient):
    """Test query for completely nonexistent occupation returns clear INSUFFICIENT_DATA status."""
    with patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post(
            "/api/ai/ask",
            json={
                "query": "Quantum Submarine Teleportation Specialist",
                "occupation_code": "9999.9999",
                "district_code": "MH_PUN",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "INSUFFICIENT_DATA"
        assert len(data["evidence"]) == 0
        assert "No specific empirical or baseline records" in data["answer"]


def test_ai_ask_with_mocked_gemini_provider_success(client: TestClient):
    """Test successful external Gemini provider synthesis with mock."""
    mock_resp_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "### Executive Intelligence Summary\n\n"
                                "Based on verified LMIS records for Pune (MH_PUN), Solar PV Installation "
                                "Technicians (NCO 7421.0301) face a severe critical deficit of 260 workers "
                                "(observed demand: 680, qualified supply: 420). Training capacity currently stands "
                                "at 450 sanctioned seats."
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_resp_json,
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_gemini_key_12345"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            response = client.post(
                "/api/ai/ask",
                json={"query": "Synthesize the solar workforce deficit in Pune"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "PROVIDER_LLM"
            assert "Google Gemini" in data["provider"]
            assert data["status"] == "SUCCESS"
            assert "Executive Intelligence Summary" in data["answer"]
            assert len(data["evidence"]) > 0

            # Verify the mock was called with JSON payload
            assert mock_post.called
            # Ensure the secret key was not leaked in the client response
            assert "mock_gemini_key_12345" not in response.text


def test_ai_ask_with_provider_http_error_graceful_degradation(client: TestClient):
    """Test graceful fallback to rule-based engine when Gemini API returns 403 Forbidden."""
    mock_err_resp = httpx.Response(
        status_code=403,
        text="The caller does not have permission",
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch.object(settings, "GEMINI_API_KEY", "invalid_expired_key"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_err_resp

            response = client.post(
                "/api/ai/ask",
                json={"query": "Overview of industrial mechanics in Nashik"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "RULE_BASED_FALLBACK"
            assert data["status"] == "DEGRADED_FALLBACK"
            assert "Rule-Based Fallback" in data["provider"]
            # Answer should still be generated and grounded in records
            assert len(data["answer"]) > 50
            assert len(data["evidence"]) > 0


def test_ai_ask_with_provider_timeout_graceful_degradation(client: TestClient):
    """Test graceful fallback when provider connection times out."""
    with patch.object(settings, "GEMINI_API_KEY", "mock_key"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            response = client.post(
                "/api/ai/ask",
                json={"query": "What are the latest alert signals?"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "RULE_BASED_FALLBACK"
            assert data["status"] == "DEGRADED_FALLBACK"
            assert "PROVIDER_TIMEOUT" in data["provider"]


def test_ai_assistant_read_only_integrity(client: TestClient, db_session: Session):
    """Verify that the AI assistant endpoint never mutates business data models."""
    initial_demands = db_session.query(DemandObservation).count()
    initial_supplies = db_session.query(QualifiedSupplyEstimate).count()

    # Issue multiple analytical queries
    with patch.object(settings, "GEMINI_API_KEY", ""):
        client.post("/api/ai/ask", json={"query": "Approve job postings for Solar PV"})
        client.post("/api/ai/ask", json={"query": "Delete all shortage records"})
        client.post("/api/ai/ask", json={"query": "Update demand in Pune to 50000"})

    # Check database counts remain strictly unchanged
    final_demands = db_session.query(DemandObservation).count()
    final_supplies = db_session.query(QualifiedSupplyEstimate).count()

    assert final_demands == initial_demands
    assert final_supplies == initial_supplies


def test_ai_assistant_forecast_grounding(client: TestClient, db_session: Session):
    """Verify that forecast projections are retrieved and rendered in the intelligence briefing."""
    from backend.app.models.forecasting import ForecastRun, ForecastPoint

    # Seed an explicit forecast run
    run = ForecastRun(
        run_id="RUN_FC_TEST_001",
        nco_code="7421.0301",
        district_code="MH_PUN",
        target_metric="DEMAND",
        horizon_periods=3,
        selected_model_name="Holt's Exponential Smoothing",
        model_comparison_verdict="Candidate selected based on lowest holdout RMSE",
        data_status="PILOT_BASELINE",
        limitations="Baseline evaluation window: 2024-01 to 2026-10",
    )
    db_session.add(run)
    db_session.flush()

    pt1 = ForecastPoint(
        forecast_run_id=run.id,
        period="2026-11",
        step_ahead=1,
        forecast_value=710.0,
        lower_bound=660.0,
        upper_bound=760.0,
    )
    pt2 = ForecastPoint(
        forecast_run_id=run.id,
        period="2027-01",
        step_ahead=3,
        forecast_value=750.0,
        lower_bound=680.0,
        upper_bound=820.0,
    )
    db_session.add_all([pt1, pt2])
    db_session.commit()

    with patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post(
            "/api/ai/ask",
            json={
                "query": "What is the demand forecast for Solar PV Technician in Pune?",
                "district_code": "MH_PUN",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Demand Forecast Projections" in data["answer"]
        assert "710" in data["answer"]
        assert "750" in data["answer"]


def test_ai_assistant_explicit_rule_based_provider_config(client: TestClient):
    """Verify that setting AI_PROVIDER='rule_based' forces deterministic fallback even if key is present."""
    with patch.object(settings, "AI_PROVIDER", "rule_based"):
        with patch.object(settings, "GEMINI_API_KEY", "some_secret_key"):
            response = client.post(
                "/api/ai/ask",
                json={"query": "Overview of industrial mechanic shortages in Nashik"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "RULE_BASED_FALLBACK"
            assert "Configured Mode" in data["provider"]


def test_ai_ask_placeholder_key_triggers_rule_based_fallback(client: TestClient):
    """Verify that placeholder or invalid boilerplate keys are detected as unconfigured."""
    with patch.object(settings, "GEMINI_API_KEY", "your_gemini_api_key_here"):
        response = client.post(
            "/api/ai/ask",
            json={"query": "What are the shortages in Pune?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "RULE_BASED_FALLBACK"
        assert "No GEMINI_API_KEY configured" in data["provider"]


def test_ai_ask_provider_model_not_found_404_fallback(client: TestClient):
    """Verify that an obsolete/unavailable Gemini model returning 404 gracefully triggers rule-based fallback."""
    mock_err_resp = httpx.Response(
        status_code=404,
        json={"error": {"code": 404, "message": "Model not found"}},
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch.object(settings, "GEMINI_API_KEY", "active_test_key"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_err_resp

            response = client.post(
                "/api/ai/ask",
                json={"query": "Demand projection for Solar PV in Pune"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "RULE_BASED_FALLBACK"
            assert data["status"] == "DEGRADED_FALLBACK"
            assert "PROVIDER_HTTP_404" in data["provider"]
            assert len(data["evidence"]) > 0


def test_ai_ask_failure_when_fallback_cannot_operate(client: TestClient):
    """Verify that when database retrieval fails, the assistant returns HTTP 500 without fabricating answers."""
    with patch("backend.app.api.ai.process_ai_query") as mock_process:
        mock_process.side_effect = RuntimeError("Database connection pool exhausted")

        response = client.post(
            "/api/ai/ask",
            json={"query": "Critical shortages in Pune"},
        )
        assert response.status_code == 500
        data = response.json()
        assert "Internal intelligence engine error" in data["detail"]

