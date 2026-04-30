"""Health endpoint tests."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.api]


def test_health(client):
    """Return an operational health status payload."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert payload["status"] == "ok"
    assert set(payload["models"]) == {"model_a", "model_b"}
