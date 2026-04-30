"""Unit tests for CI smoke helper scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


class _FakeResponse:
    """Minimal response stub matching `requests.Response` surface used by scripts."""

    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        """Store synthetic HTTP response state."""
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        """Return pre-seeded JSON payload."""
        return self._payload


def _load_script_module(script_name: str):
    """Load a script file as an importable module for unit testing."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_smoke_serving_run_success(monkeypatch):
    """Pass smoke serving when health and predict endpoints respond correctly."""
    smoke_serving = _load_script_module("smoke_serving.py")

    def fake_get(url, timeout):  # noqa: ARG001
        return _FakeResponse(200, {"data": {"models": ["model_a", "model_b"]}})

    def fake_post(url, json, timeout):  # noqa: ARG001
        return _FakeResponse(
            200,
            {
                "data": {
                    "model_name": "model_a",
                    "top1_label": "carrot",
                    "top1_conf": 0.9,
                    "topk": [{"label": "carrot", "confidence": 0.9}],
                    "latency_ms": 12.3,
                }
            },
        )

    monkeypatch.setattr(smoke_serving.requests, "get", fake_get)
    monkeypatch.setattr(smoke_serving.requests, "post", fake_post)

    smoke_serving.run(base_url="http://127.0.0.1:8000", model_name="model_a", wait_seconds=5)


def test_smoke_webapp_run_success(monkeypatch):
    """Pass web smoke when backend health/models/pages are available."""
    smoke_webapp = _load_script_module("smoke_webapp.py")

    def fake_get(url, timeout):  # noqa: ARG001
        if url.endswith("/api/health"):
            return _FakeResponse(200, {"data": {"status": "ok", "models": ["model_a"]}})
        if url.endswith("/api/models"):
            return _FakeResponse(200, {"data": {"models": [{"name": "model_a"}]}})
        if url.endswith("/"):
            return _FakeResponse(200, text="<html>VeggieAI</html>")
        if url.endswith("/auth"):
            return _FakeResponse(200, text="<html>VeggieAI Sign In</html>")
        return _FakeResponse(404, text="missing")

    monkeypatch.setattr(smoke_webapp.requests, "get", fake_get)

    smoke_webapp.run(base_url="http://127.0.0.1:5000", wait_seconds=5)


def test_smoke_webapp_fails_when_model_list_empty(monkeypatch):
    """Fail web smoke when `/api/models` returns an empty model set."""
    smoke_webapp = _load_script_module("smoke_webapp.py")

    def fake_get(url, timeout):  # noqa: ARG001
        if url.endswith("/api/health"):
            return _FakeResponse(200, {"data": {"status": "ok", "models": ["model_a"]}})
        if url.endswith("/api/models"):
            return _FakeResponse(200, {"data": {"models": []}})
        return _FakeResponse(200, text="<html>VeggieAI</html>")

    monkeypatch.setattr(smoke_webapp.requests, "get", fake_get)

    with pytest.raises(RuntimeError):
        smoke_webapp.run(base_url="http://127.0.0.1:5000", wait_seconds=5)
