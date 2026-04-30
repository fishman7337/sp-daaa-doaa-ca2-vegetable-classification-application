"""History API tests for query filtering, paging, and user data isolation."""

from __future__ import annotations

import io

import pytest
import responses

from .conftest import make_image_bytes

pytestmark = [pytest.mark.api]


def _login(client):
    """Authenticate admin and return a JWT token."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return resp.get_json()["data"]["token"]


def _signup_and_login(client, email: str):
    """Create a user account and return an authenticated JWT."""
    signup = client.post(
        "/api/auth/signup",
        json={"name": "Secondary User", "email": email, "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201
    login = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    assert login.status_code == 200
    return login.get_json()["data"]["token"]


def _create_prediction(client, token, label="happy"):
    """Insert a synthetic prediction through the `/api/predict` endpoint."""
    responses.add(
        responses.POST,
        "http://model-service/predict",
        json={
            "data": {
                "model_name": "model_a",
                "top1_label": label,
                "top1_conf": 0.85,
                "topk": [
                    {"label": label, "confidence": 0.85},
                    {"label": "neutral", "confidence": 0.1},
                ],
                "latency_ms": 14.2,
            }
        },
        status=200,
    )
    image_bytes = make_image_bytes()
    return client.post(
        "/api/predict",
        data={
            "model_name": "model_a",
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )


@responses.activate
@pytest.mark.expected_failure
def test_history_requires_auth(client):
    """Reject unauthenticated history requests."""
    resp = client.get("/api/history")
    assert resp.status_code == 401


@responses.activate
@pytest.mark.validity
def test_history_search_and_pagination(client):
    """Support search filters and pagination metadata."""
    token = _login(client)
    first = _create_prediction(client, token, label="happy")
    _create_prediction(client, token, label="sad")
    resp = client.get(
        "/api/history?q=label:happy&page=1&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert payload["page"]["page_size"] == 1
    assert payload["items"][0]["top1_label"] == "happy"

    history_id = first.get_json()["data"]["history_id"]
    detail = client.get(f"/api/history/{history_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200


@pytest.mark.range
@pytest.mark.expected_failure
def test_history_page_size_bounds(client):
    """Reject `page_size` values outside allowed range."""
    token = _login(client)
    resp = client.get("/api/history?page_size=1000", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@responses.activate
@pytest.mark.consistency
def test_history_is_scoped_to_authenticated_user(client):
    """Ensure users cannot read each other's prediction history records."""
    admin_token = _login(client)
    user_token = _signup_and_login(client, "history-user@example.com")

    admin_prediction = _create_prediction(client, admin_token, label="admin-label")
    user_prediction = _create_prediction(client, user_token, label="user-label")

    admin_history = client.get("/api/history", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_history.status_code == 200
    admin_items = admin_history.get_json()["data"]["items"]
    assert len(admin_items) == 1
    assert admin_items[0]["top1_label"] == "admin-label"

    user_history = client.get("/api/history", headers={"Authorization": f"Bearer {user_token}"})
    assert user_history.status_code == 200
    user_items = user_history.get_json()["data"]["items"]
    assert len(user_items) == 1
    assert user_items[0]["top1_label"] == "user-label"

    admin_history_id = admin_prediction.get_json()["data"]["history_id"]
    user_history_id = user_prediction.get_json()["data"]["history_id"]

    assert (
        client.get(f"/api/history/{admin_history_id}", headers={"Authorization": f"Bearer {user_token}"}).status_code
        == 404
    )
    assert (
        client.get(f"/api/history/{user_history_id}", headers={"Authorization": f"Bearer {admin_token}"}).status_code
        == 404
    )


@responses.activate
def test_history_image_and_delete_flow(client):
    """Serve history image and support deleting the history record."""
    token = _login(client)
    created = _create_prediction(client, token, label="image-delete")
    assert created.status_code == 201
    history_id = created.get_json()["data"]["history_id"]

    image_response = client.get(f"/api/history/{history_id}/image", headers={"Authorization": f"Bearer {token}"})
    assert image_response.status_code == 200
    assert (image_response.headers.get("Content-Type") or "").startswith("image/")

    deleted = client.delete(f"/api/history/{history_id}", headers={"Authorization": f"Bearer {token}"})
    assert deleted.status_code == 200
    assert deleted.get_json()["data"]["deleted"] is True

    missing = client.get(f"/api/history/{history_id}", headers={"Authorization": f"Bearer {token}"})
    assert missing.status_code == 404


@responses.activate
def test_history_image_returns_404_when_file_disappears_before_send(client, monkeypatch):
    """Return 404 instead of 500 when image vanishes during send_file."""
    token = _login(client)
    created = _create_prediction(client, token, label="race")
    assert created.status_code == 201
    history_id = created.get_json()["data"]["history_id"]

    def _raise_file_not_found(*_args, **_kwargs):
        raise FileNotFoundError("simulated race during send_file")

    monkeypatch.setattr("backend.history.send_file", _raise_file_not_found)
    image_response = client.get(f"/api/history/{history_id}/image", headers={"Authorization": f"Bearer {token}"})
    assert image_response.status_code == 404
    assert image_response.get_json()["error"]["code"] == "not_found"
