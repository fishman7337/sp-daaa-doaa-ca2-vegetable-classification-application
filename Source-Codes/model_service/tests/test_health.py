"""Health endpoint tests for the model service."""

import pytest

pytestmark = [pytest.mark.api]


def test_health(client):
    """Return a healthy status response."""
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert payload["status"] == "ok"
    assert set(payload["models"]) == {"model_a", "model_b"}
