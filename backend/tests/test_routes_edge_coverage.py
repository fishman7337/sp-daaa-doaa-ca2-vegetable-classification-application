"""Edge coverage for route helpers and browser compatibility routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from flask import current_app

from backend.history import _parse_int, _resolve_image_mimetype
from backend.utils.jwt import create_token
from backend.views import _session_user_payload

pytestmark = [pytest.mark.unit]


def test_history_helper_edges():
    """Cover fallback parsing and MIME fallback behavior."""
    assert _parse_int("42", 1) == 42
    assert _parse_int("not-a-number", 7) == 7
    assert _parse_int(None, 3) == 3
    assert _resolve_image_mimetype(Path("photo.png")) == "image/png"
    assert _resolve_image_mimetype(Path("unknown.bin")) == "image/jpeg"


def test_session_user_payload_defaults():
    """Build safe template user payloads with and without avatar fields."""
    with_avatar = _session_user_payload(
        {
            "id": 1,
            "username": "admin",
            "email": "admin@example.test",
            "display_name": "",
            "role": "admin",
            "avatar": "avatar.png",
        }
    )
    without_avatar = _session_user_payload(
        {"id": 2, "username": "", "email": "", "display_name": "", "role": "user", "avatar": ""}
    )

    assert with_avatar["name"] == "admin"
    assert with_avatar["avatar"] == "avatar.png"
    assert without_avatar["name"] == "User"
    assert without_avatar["avatar"] == ""


def test_legacy_browser_routes_redirect(client):
    """Maintain compatibility redirects for older browser routes."""
    for route in ["/logout", "/web/logout", "/web/login", "/web/register", "/web/predict", "/web/history"]:
        response = client.get(route)
        assert response.status_code in {302, 308}


def test_theme_route_get_post_and_validation(client):
    """Persist and validate browser theme preferences."""
    get_response = client.get("/web/theme")
    assert get_response.status_code == 200
    assert get_response.get_json()["data"]["theme"] in {"dark", "light"}

    invalid = client.post("/web/theme", json={"theme": "blue"})
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "validation_error"

    valid = client.post("/web/theme", json={"theme": "light"})
    assert valid.status_code == 200
    assert valid.get_json()["data"]["theme"] == "light"
    assert "veggie-theme=light" in valid.headers.get("Set-Cookie", "")


def test_session_login_validation_and_success_paths(client, auth_token):
    """Exercise browser session bridge validation and success branches."""
    missing = client.post("/web/session/login", json={})
    assert missing.status_code == 400

    invalid = client.post("/web/session/login", json={"token": "not-a-token"})
    assert invalid.status_code == 401

    valid = client.post("/web/session/login", json={"token": auth_token})
    assert valid.status_code == 200
    assert valid.get_json()["data"]["authenticated"] is True

    auth_page = client.get("/auth")
    assert auth_page.status_code == 302

    history_page = client.get("/history")
    assert history_page.status_code == 302
    assert "tab=history" in history_page.headers["Location"]

    logout = client.post("/web/session/logout")
    assert logout.status_code == 200


def test_session_login_rejects_bad_payload_and_missing_user(client, app):
    """Cover invalid-token payload and deleted-user session bridge branches."""
    with app.app_context():
        bad_payload_token = jwt.encode(
            {
                "role": "user",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            },
            current_app.config["JWT_SECRET"],
            algorithm="HS256",
        )
        missing_user_token = create_token(9999, "ghost", "user")

    bad_payload = client.post("/web/session/login", json={"token": bad_payload_token})
    assert bad_payload.status_code == 401

    missing_user = client.post("/web/session/login", json={"token": missing_user_token})
    assert missing_user.status_code == 404


def test_registered_error_handlers_return_json(app):
    """Normalize 404 and unexpected exceptions through the app handlers."""

    @app.get("/raise-for-test")
    def _raise_for_test():
        raise RuntimeError("boom")

    not_found = app.test_client().get("/not-found-for-test")
    assert not_found.status_code == 404
    assert not_found.get_json()["error"]["code"] == "http_error"

    unexpected = app.test_client().get("/raise-for-test")
    assert unexpected.status_code == 500
    assert unexpected.get_json()["error"]["code"] == "internal_error"
    assert unexpected.get_json()["error"]["details"] == "boom"


def test_history_query_validation_edges(client, auth_headers):
    """Exercise invalid history query validation branches."""
    for query in ["page_size=0", "date_from=bad", "date_to=bad", "conf_min=bad", "conf_max=bad", "latency_max=bad"]:
        response = client.get(f"/api/history?{query}", headers=auth_headers)
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "validation_error"
