"""Read-only transport tests; synthetic fixtures never become study evidence."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import research_workflow as route
from app.main import app


def test_workflow_is_fresh_and_read_only(monkeypatch):
    monkeypatch.setattr(
        route, "build_workflow", lambda root: {"state": "DATA_REVIEW_PENDING"}
    )
    with TestClient(app) as client:
        result = client.get("/api/v1/research/workflow")
        assert result.status_code == 200
        assert result.json()["state"] == "DATA_REVIEW_PENDING"
        assert result.headers["cache-control"] == "no-store"
        assert client.post("/api/v1/research/workflow").status_code == 405


@pytest.mark.parametrize("error", [ValueError, AttributeError])
def test_invalid_evidence_has_sanitized_retryable_error(monkeypatch, error):
    def invalid(root):
        raise error("/Users/private/reviewer.json")

    monkeypatch.setattr(route, "build_workflow", invalid)
    with TestClient(app) as client:
        response = client.get("/api/v1/research/workflow")
        assert response.status_code == 503
        assert "/Users" not in response.text
        assert response.headers["cache-control"] == "no-store"


def test_only_unfilled_templates_are_downloadable():
    with TestClient(app) as client:
        response = client.get("/api/v1/research/templates/retrieval_observations.csv")
        assert response.status_code == 200
        assert "participant_id" in response.text
        assert response.headers["cache-control"] == "no-store"
        for name in ["methodology_review.json", "approval.json", "not-a-template.csv"]:
            assert client.get(f"/api/v1/research/templates/{name}").status_code == 404
