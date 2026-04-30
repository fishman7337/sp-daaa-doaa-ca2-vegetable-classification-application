"""Model metadata API tests."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.api]


def test_models_list(client):
    """Return configured backend model list payload."""
    resp = client.get("/api/models")
    assert resp.status_code == 200
    payload = resp.get_json()["data"]["models"]
    names = {entry["name"] for entry in payload}
    assert names == {"model_a", "model_b"}
