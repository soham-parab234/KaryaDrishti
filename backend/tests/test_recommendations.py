"""Tests for Phase 10: Decision Intelligence & Policy Recommendations."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.recommendations import PolicyRecommendation
from backend.app.services.recommendations_service import generate_policy_recommendations


def test_generate_policy_recommendations_service(db_session: Session):
    """Verify that recommendations service analyzes evidence and produces valid recommendations."""
    res = generate_policy_recommendations(db_session)
    assert res.total_recommendations > 0
    assert len(res.items) == res.total_recommendations
    assert res.expansion_count + res.curriculum_pivot_count + res.apprenticeship_count + res.data_audit_count == res.total_recommendations

    # Check structural integrity of each recommendation
    for item in res.items:
        assert item.recommendation_id.startswith("REC-")
        assert item.nco_code is not None
        assert item.district_code is not None
        assert item.recommendation_type in {
            "TRAINING_CAPACITY_EXPANSION",
            "CURRICULUM_MODERNIZATION_OR_PIVOT",
            "APPRENTICESHIP_INDUSTRY_TIE_UP",
            "DATA_COLLECTION_AUDIT",
        }
        assert item.priority in {"HIGH", "MEDIUM", "LOW"}
        assert len(item.action_title) > 5
        assert len(item.rationale) > 20
        assert 0.0 <= item.feasibility_score <= 1.0
        assert item.data_status in {
            "CONFIRMED_OBSERVATION",
            "PROJECTION_BASED",
            "DATA_DEFICIT_ADVISORY",
            "SYNTHETIC_DEMO",
        }
        assert isinstance(item.evidence_sources, dict)
        assert isinstance(item.limitations, list)
        assert len(item.limitations) > 0


def test_api_list_recommendations(client: TestClient):
    """Verify GET /api/recommendations endpoint and filtering capabilities."""
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "total_recommendations" in data
    assert "items" in data
    assert data["total_recommendations"] > 0

    # Filter by priority if available
    high_priority_resp = client.get("/api/recommendations?priority=HIGH")
    assert high_priority_resp.status_code == 200
    high_data = high_priority_resp.json()
    for item in high_data["items"]:
        assert item["priority"] == "HIGH"

    # Filter by non-existent occupation should return empty items
    empty_resp = client.get("/api/recommendations?nco_code=NON_EXISTENT_9999")
    assert empty_resp.status_code == 200
    assert empty_resp.json()["total_recommendations"] == 0
    assert empty_resp.json()["items"] == []


def test_api_evaluate_recommendations_endpoint(client: TestClient):
    """Verify POST /api/recommendations/evaluate regenerates recommendations idempotently."""
    post_res = client.post("/api/recommendations/evaluate")
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["total_recommendations"] > 0

    # Second call should be idempotent and not create duplicate recommendations
    second_res = client.post("/api/recommendations/evaluate")
    assert second_res.status_code == 200
    second_data = second_res.json()
    assert second_data["total_recommendations"] == data["total_recommendations"]


def test_recompute_pipeline_triggers_recommendations(client: TestClient):
    """Verify that recomputing pipeline refreshes recommendations count in the response."""
    recompute_res = client.post("/api/analytics/recompute-pipeline")
    assert recompute_res.status_code == 200
    data = recompute_res.json()
    assert "recommendations_generated" in data
    assert data["recommendations_generated"] > 0
    assert "actionable policy recommendation" in data["message"]
