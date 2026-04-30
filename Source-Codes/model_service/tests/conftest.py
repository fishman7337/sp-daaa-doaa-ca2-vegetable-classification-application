"""Shared fixtures for model-service API tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from model_service.app import create_app


@pytest.fixture()
def app():
    """Create a mock-mode model-service Flask app."""
    config = {
        "MODEL_MODE": "mock",
        "MODELS_ROOT": str(Path(__file__).resolve().parents[2] / "models"),
    }
    app = create_app(config)
    return app


@pytest.fixture()
def client(app):
    """Return a Flask test client for model-service tests."""
    return app.test_client()
