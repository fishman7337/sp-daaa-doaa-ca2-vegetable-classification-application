"""Security hardening tests for headers, auth controls, and injection resistance."""

from __future__ import annotations

import io
from urllib.parse import quote_plus

import pytest

from .conftest import make_image_bytes

pytestmark = [pytest.mark.security, pytest.mark.api]


@pytest.mark.parametrize(
    "path",
    [
        "/api/health",
        "/api/auth/captcha",
    ],
)
def test_security_headers_present(client, path: str):
    """Apply hardened response headers on public endpoints."""
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
    assert response.headers.get("Permissions-Policy") == "camera=(self), microphone=(), geolocation=()"
    assert response.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert response.headers.get("Cross-Origin-Resource-Policy") == "same-origin"
    assert "frame-ancestors 'none'" in (response.headers.get("Content-Security-Policy") or "")
    assert response.headers.get("Strict-Transport-Security", "").startswith("max-age=")


@pytest.mark.parametrize(
    ("path", "method", "payload"),
    [
        ("/api/auth/login", "post", {"username": "admin", "password": "wrong"}),
        ("/api/chat/history", "get", None),
    ],
)
def test_sensitive_endpoints_disable_caching(client, path: str, method: str, payload):
    """Disable caching on sensitive authentication and chat endpoints."""
    if method == "post":
        response = client.post(path, json=payload)
    else:
        response = client.get(path)
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"


@pytest.mark.parametrize(
    "malicious_username",
    [
        "' OR 1=1 --",
        "admin' --",
        '" OR "1"="1',
    ],
)
def test_login_rejects_sql_injection_attempts(client, malicious_username: str):
    """Reject classic SQL injection payloads in login identifiers."""
    response = client.post("/api/auth/login", json={"username": malicious_username, "password": "irrelevant"})
    assert response.status_code in {400, 401}


@pytest.mark.parametrize(
    "malicious_query",
    [
        "' OR 1=1 --",
        "label:happy'; DROP TABLE users; --",
        '" OR "1"="1',
    ],
)
def test_history_search_resists_sql_injection(client, auth_headers, malicious_query: str):
    """Handle malicious search text without breaking query execution."""
    url = f"/api/history?q={quote_plus(malicious_query)}"
    response = client.get(url, headers=auth_headers)
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert "items" in payload


def test_query_token_allowed_only_for_image_endpoint(client, auth_headers, auth_token):
    """Allow query-string token only on image retrieval endpoints."""
    image_bytes = make_image_bytes()
    prediction = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert prediction.status_code == 201
    image_path = prediction.get_json()["data"]["prediction"]["image"]

    image_response = client.get(f"{image_path}?token={auth_token}")
    assert image_response.status_code == 200
    assert (image_response.headers.get("Content-Type") or "").startswith("image/")
