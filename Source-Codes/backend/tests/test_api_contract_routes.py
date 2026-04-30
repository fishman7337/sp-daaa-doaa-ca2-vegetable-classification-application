"""API contract tests for crucial Flask REST endpoints."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.api]


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/health", "GET"),
        ("/api/models", "GET"),
        ("/api/predict", "POST"),
        ("/api/history", "GET"),
        ("/api/history/<int:prediction_id>", "GET"),
        ("/api/auth/login", "POST"),
        ("/api/auth/signup", "POST"),
        ("/api/auth/register", "POST"),
        ("/api/auth/me", "GET"),
        ("/api/veggie/models", "GET"),
        ("/api/veggie/catalog", "GET"),
        ("/api/veggie/prices", "GET"),
        ("/api/veggie/predict", "POST"),
        ("/api/veggie/detect", "POST"),
        ("/api/veggie/history", "GET"),
        ("/api/chat/message", "POST"),
        ("/api/chat/history", "GET"),
        ("/api/chat/history", "DELETE"),
        ("/api/chat/conversations", "GET"),
        ("/api/chat/conversations", "POST"),
    ],
)
def test_crucial_rest_routes_are_registered(app, path: str, method: str) -> None:
    """Expose required CRUD/prediction/chat endpoints in Flask URL map."""
    url_map = app.url_map
    rules = [rule for rule in url_map.iter_rules() if rule.rule == path and method in rule.methods]
    assert rules, f"Route {method} {path} is missing from Flask URL map"
