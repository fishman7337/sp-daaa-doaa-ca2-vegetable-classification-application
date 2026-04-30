"""Penetration-style security tests for auth, transport, and access controls."""

from __future__ import annotations

import io
import time
from urllib.parse import quote_plus

import jwt
import pytest

from .conftest import make_image_bytes

pytestmark = [pytest.mark.security, pytest.mark.api]


def _make_headers(token: str) -> dict[str, str]:
    """Build bearer authorization headers."""
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("max_attempts", [2, 3])
def test_login_rate_limit_blocks_bruteforce(client, max_attempts: int):
    """Block repeated invalid login attempts after threshold is reached."""
    client.application.config["RATE_LIMIT_MAX"] = max_attempts
    client.application.config["RATE_LIMIT_WINDOW_SEC"] = 300

    for _ in range(max_attempts):
        invalid = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"})
        assert invalid.status_code == 401

    blocked = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert blocked.status_code == 429
    assert blocked.get_json()["error"]["code"] == "rate_limited"


def test_login_rate_limit_resets_after_successful_login(client):
    """Reset rate limiter state after successful authentication."""
    client.application.config["RATE_LIMIT_MAX"] = 2
    client.application.config["RATE_LIMIT_WINDOW_SEC"] = 300

    invalid = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert invalid.status_code == 401

    success = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert success.status_code == 200

    invalid_after_success = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert invalid_after_success.status_code == 401


def test_captcha_challenge_cannot_be_replayed(client, solve_captcha):
    """Invalidate captcha challenges after one successful use."""
    client.application.config["CAPTCHA_ENABLED"] = True
    client.application.config["CAPTCHA_DEV_MODE"] = True
    client.application.config["OTP_ENABLED"] = False

    challenge = client.get("/api/auth/captcha")
    assert challenge.status_code == 200
    challenge_payload = challenge.get_json()["data"]
    answer = solve_captcha(challenge_payload)

    first_login = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123",
            "captcha_id": challenge_payload["captcha_id"],
            "captcha_answer": answer,
        },
    )
    assert first_login.status_code == 200

    replay_login = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123",
            "captcha_id": challenge_payload["captcha_id"],
            "captcha_answer": answer,
        },
    )
    assert replay_login.status_code == 400
    assert replay_login.get_json()["error"]["code"] in {"captcha_invalid", "captcha_expired"}


def test_otp_session_locks_after_max_attempts(client):
    """Lock and invalidate OTP sessions after configured failed attempts."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = True
    client.application.config["OTP_DEV_MODE"] = True
    client.application.config["OTP_MAX_ATTEMPTS"] = 2

    signup = client.post(
        "/api/auth/signup",
        json={"name": "OTP User", "email": "otp-lock@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201
    signup_payload = signup.get_json()["data"]
    session_id = signup_payload["otp_session"]
    valid_code = signup_payload["dev_otp"]

    first_wrong = client.post("/api/auth/otp/verify", json={"otp_session": session_id, "otp_code": "000000"})
    assert first_wrong.status_code == 401
    assert first_wrong.get_json()["error"]["code"] == "invalid_otp"

    second_wrong = client.post("/api/auth/otp/verify", json={"otp_session": session_id, "otp_code": "000000"})
    assert second_wrong.status_code == 401
    assert second_wrong.get_json()["error"]["code"] == "otp_locked"

    after_lock = client.post("/api/auth/otp/verify", json={"otp_session": session_id, "otp_code": valid_code})
    assert after_lock.status_code == 400
    assert after_lock.get_json()["error"]["code"] == "invalid_otp_session"


@pytest.mark.parametrize("token_kind", ["tampered", "wrong_secret", "expired"])
def test_invalid_and_expired_tokens_are_rejected(client, auth_token, token_kind: str):
    """Reject tampered, wrong-secret, and expired JWT tokens."""
    secret = client.application.config["JWT_SECRET"]
    if token_kind == "tampered":
        token = f"{auth_token}corrupted"
    elif token_kind == "wrong_secret":
        payload = jwt.decode(auth_token, options={"verify_signature": False})
        token = jwt.encode(payload, "not-the-right-secret", algorithm="HS256")
    else:
        now_epoch = int(time.time())
        payload = {
            "sub": "1",
            "username": "admin",
            "role": "admin",
            "iat": now_epoch - 7200,
            "exp": now_epoch - 3600,
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

    response = client.get("/api/auth/me", headers=_make_headers(token))
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] in {"invalid_token", "token_expired"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/me",
        "/api/history",
        "/api/chat/history",
        "/api/veggie/history",
    ],
)
def test_query_token_is_rejected_for_non_image_endpoints(client, auth_token, path: str):
    """Disallow query-token authentication on non-image routes."""
    response = client.get(f"{path}?token={quote_plus(auth_token)}")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("http://localhost:3000", True),
        ("https://evil.example", False),
    ],
)
def test_cors_allows_only_configured_origins(client, origin: str, allowed: bool):
    """Only emit CORS allow headers for configured origins."""
    response = client.get("/api/health", headers={"Origin": origin})
    header_value = response.headers.get("Access-Control-Allow-Origin")
    if allowed:
        assert header_value == origin
    else:
        assert header_value is None


def test_force_https_redirects_plain_http_when_enabled(client):
    """Redirect plain HTTP requests to HTTPS when enforcement is enabled."""
    client.application.config["TESTING"] = False
    client.application.config["FORCE_HTTPS"] = True

    redirected = client.get("/api/health", base_url="http://veggie.local")
    assert redirected.status_code == 308
    assert redirected.headers.get("Location") == "https://veggie.local/api/health"

    already_secure = client.get(
        "/api/health",
        base_url="http://veggie.local",
        headers={"X-Forwarded-Proto": "https"},
    )
    assert already_secure.status_code == 200


def test_veggie_image_endpoint_resists_cross_user_idor(client, auth_token, bearer_headers, signup_and_login):
    """Prevent cross-user image access via IDOR attempts."""
    client.application.config["VEGNET_REMOTE_ENABLED"] = True

    other_token = signup_and_login("idor-user@example.com")
    image_bytes = make_image_bytes()
    create = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "owner.png"), "model_name": "vegnet-23"},
        headers=bearer_headers(auth_token),
        content_type="multipart/form-data",
    )
    assert create.status_code == 201
    prediction_id = create.get_json()["data"]["prediction"]["id"]

    path = f"/api/veggie/history/{prediction_id}/image"
    via_header = client.get(path, headers=bearer_headers(other_token))
    assert via_header.status_code == 404

    via_query = client.get(f"{path}?token={quote_plus(other_token)}")
    assert via_query.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/history",
        "/api/veggie/history",
        "/api/veggie/catalog",
        "/api/chat/history",
    ],
)
def test_authenticated_api_responses_disable_caching(client, auth_headers, path: str):
    """Disable caching headers on authenticated API responses."""
    response = client.get(path, headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"


@pytest.mark.parametrize(
    ("path", "form_data"),
    [
        ("/api/predict", {"model_name": "model_a"}),
        ("/api/veggie/predict", {"model_name": "vegnet-23"}),
    ],
)
def test_non_image_payloads_are_rejected(client, auth_headers, path: str, form_data: dict):
    """Reject script-like non-image uploads on prediction endpoints."""
    malformed = dict(form_data)
    malformed["image"] = (io.BytesIO(b"<script>alert('xss')</script>"), "payload.txt")

    response = client.post(
        path,
        data=malformed,
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_image"


@pytest.mark.parametrize("path", ["/api/auth/me", "/api/chat/history", "/api/veggie/history"])
def test_security_headers_are_present_on_auth_errors(client, path: str):
    """Return hardened response headers even on auth failures."""
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
