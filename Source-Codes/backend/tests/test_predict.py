"""Prediction API tests for model selection, validation, and resiliency."""

from __future__ import annotations

import io

import pytest
import requests
import responses

from .conftest import make_image_bytes

pytestmark = [pytest.mark.api]


def _login(client):
    """Authenticate the admin user and return a bearer token."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return resp.get_json()["data"]["token"]


@responses.activate
@pytest.mark.validity
@pytest.mark.range
def test_predict_happy_path(client):
    """Persist prediction output for a valid model and image payload."""
    token = _login(client)
    responses.add(
        responses.POST,
        "http://model-service/predict",
        json={
            "data": {
                "model_name": "model_a",
                "top1_label": "happy",
                "top1_conf": 0.91,
                "topk": [
                    {"label": "happy", "confidence": 0.91},
                    {"label": "neutral", "confidence": 0.08},
                ],
                "latency_ms": 12.5,
            }
        },
        status=200,
    )
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/predict",
        data={
            "model_name": "model_a",
            "input_type": "upload",
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    payload = resp.get_json()["data"]
    assert payload["prediction"]["top1_conf"] == 0.91
    assert 0 <= payload["prediction"]["top1_conf"] <= 1
    assert payload["prediction"]["latency_ms"] > 0


@responses.activate
@pytest.mark.validity
@pytest.mark.expected_failure
def test_predict_rejects_non_image(client):
    """Reject uploads that are not valid image files."""
    token = _login(client)
    resp = client.post(
        "/api/predict",
        data={
            "model_name": "model_a",
            "image": (io.BytesIO(b"not-image"), "bad.txt"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


@responses.activate
@pytest.mark.validity
@pytest.mark.expected_failure
def test_predict_unsupported_model(client):
    """Reject predictions for unknown model names."""
    token = _login(client)
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/predict",
        data={
            "model_name": "missing",
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


@pytest.mark.validity
@pytest.mark.expected_failure
def test_predict_requires_model_name(client):
    """Reject predictions without a selected model name."""
    token = _login(client)
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/predict",
        data={
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "validation_error"


@pytest.mark.unexpected_failure
def test_predict_model_service_unreachable(client, monkeypatch):
    """Return service unavailable when inference backend cannot be reached."""
    token = _login(client)
    image_bytes = make_image_bytes()

    def _raise(*args, **kwargs):
        """Raise a connection error for resilience testing."""
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "post", _raise)
    resp = client.post(
        "/api/predict",
        data={
            "model_name": "model_a",
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 503


@responses.activate
@pytest.mark.unexpected_failure
def test_predict_model_service_incomplete_payload(client):
    """Return bad gateway when model service payload misses required fields."""
    token = _login(client)
    responses.add(
        responses.POST,
        "http://model-service/predict",
        json={"data": {"top1_label": "happy"}},
        status=200,
    )
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/predict",
        data={
            "model_name": "model_a",
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 502
    assert resp.get_json()["error"]["code"] == "model_service_error"


@responses.activate
@pytest.mark.unexpected_failure
def test_predict_model_service_invalid_json(client):
    """Return bad gateway when model service returns non-JSON response body."""
    token = _login(client)
    responses.add(
        responses.POST,
        "http://model-service/predict",
        body="not-json",
        status=200,
        content_type="text/plain",
    )
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/predict",
        data={
            "model_name": "model_a",
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 502
    assert resp.get_json()["error"]["code"] == "model_service_error"


@responses.activate
@pytest.mark.consistency
def test_predict_consistency_hash(client):
    """Return identical image hashes for repeated uploads of same bytes."""
    token = _login(client)
    responses.add(
        responses.POST,
        "http://model-service/predict",
        json={
            "data": {
                "model_name": "model_a",
                "top1_label": "happy",
                "top1_conf": 0.6,
                "topk": [
                    {"label": "happy", "confidence": 0.6},
                    {"label": "neutral", "confidence": 0.3},
                ],
                "latency_ms": 10.0,
            }
        },
        status=200,
    )
    responses.add(
        responses.POST,
        "http://model-service/predict",
        json={
            "data": {
                "model_name": "model_a",
                "top1_label": "happy",
                "top1_conf": 0.6,
                "topk": [
                    {"label": "happy", "confidence": 0.6},
                    {"label": "neutral", "confidence": 0.3},
                ],
                "latency_ms": 10.0,
            }
        },
        status=200,
    )
    image_bytes = make_image_bytes()
    resp1 = client.post(
        "/api/predict",
        data={"model_name": "model_a", "image": (io.BytesIO(image_bytes), "sample.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    resp2 = client.post(
        "/api/predict",
        data={"model_name": "model_a", "image": (io.BytesIO(image_bytes), "sample.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.get_json()["data"]["sha256"] == resp2.get_json()["data"]["sha256"]
