"""Unit tests for JWT helper edge cases and session fallbacks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from flask import current_app, g, jsonify, session

from backend.utils.jwt import _session_jwt_payload, create_token, jwt_required

pytestmark = [pytest.mark.unit, pytest.mark.security]


def _expired_token(secret: str) -> str:
    """Build an already-expired token for authentication failure paths."""
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "1",
            "username": "admin",
            "role": "admin",
            "iat": int((now - timedelta(minutes=10)).timestamp()),
            "exp": int((now - timedelta(minutes=5)).timestamp()),
        },
        secret,
        algorithm="HS256",
    )


def test_session_jwt_payload_rejects_missing_malformed_and_mismatched_session_state(app):
    """Return None for unsafe Flask session state instead of trusting it."""
    with app.test_request_context("/"):
        assert _session_jwt_payload() is None

        session["token"] = "not-a-jwt"
        session["user"] = {"id": 1}
        assert _session_jwt_payload() is None

        session["token"] = create_token(1, "admin", "admin")
        session["user"] = ["not", "a", "dict"]
        assert _session_jwt_payload() is None

        session["user"] = {"id": 2}
        assert _session_jwt_payload() is None


def test_session_jwt_payload_accepts_consistent_session_state(app):
    """Decode a valid session token only when the session user matches it."""
    with app.test_request_context("/"):
        session["token"] = create_token(1, "admin", "admin")
        session["user"] = {"id": 1}

        payload = _session_jwt_payload()
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "admin"


def test_jwt_required_supports_query_tokens_and_reports_auth_errors(app):
    """Cover explicit query-token support plus missing and invalid token responses."""

    @app.get("/test-jwt/query")
    @jwt_required(allow_query_token=True)
    def _query_token_route():
        return jsonify({"sub": g.user["sub"]})

    with app.app_context():
        token = create_token(1, "admin", "admin")

    client = app.test_client()
    missing = client.get("/test-jwt/query")
    assert missing.status_code == 401
    assert missing.get_json()["error"]["code"] == "unauthorized"

    invalid = client.get("/test-jwt/query?token=not-a-jwt")
    assert invalid.status_code == 401
    assert invalid.get_json()["error"]["code"] == "invalid_token"

    valid = client.get(f"/test-jwt/query?token={token}")
    assert valid.status_code == 200
    assert valid.get_json()["sub"] == "1"


def test_jwt_required_uses_session_fallback_for_bad_header_token(app):
    """Use a valid Flask session token when browser routes receive bad headers."""

    @app.get("/test-jwt/session-fallback")
    @jwt_required(allow_session_user=True)
    def _session_fallback_route():
        return jsonify({"sub": g.user["sub"]})

    with app.app_context():
        session_token = create_token(1, "admin", "admin")
        expired = _expired_token(current_app.config["JWT_SECRET"])

    client = app.test_client()
    with client.session_transaction() as stored_session:
        stored_session["token"] = session_token
        stored_session["user"] = {"id": 1}

    no_header = client.get("/test-jwt/session-fallback")
    assert no_header.status_code == 200
    assert no_header.get_json()["sub"] == "1"

    invalid_header = client.get("/test-jwt/session-fallback", headers={"Authorization": "Bearer not-a-jwt"})
    assert invalid_header.status_code == 200
    assert invalid_header.get_json()["sub"] == "1"

    expired_header = client.get("/test-jwt/session-fallback", headers={"Authorization": f"Bearer {expired}"})
    assert expired_header.status_code == 200
    assert expired_header.get_json()["sub"] == "1"


def test_jwt_required_reports_expired_token_without_session_fallback(app):
    """Return token_expired when no session fallback is enabled."""

    @app.get("/test-jwt/expired")
    @jwt_required
    def _expired_route():
        return jsonify({"sub": g.user["sub"]})

    with app.app_context():
        expired = _expired_token(current_app.config["JWT_SECRET"])

    response = app.test_client().get("/test-jwt/expired", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "token_expired"
