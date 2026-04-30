"""Prediction endpoint tests for the model service."""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

pytestmark = [pytest.mark.api]


def _make_image_bytes():
    """Create an in-memory PNG image payload."""
    img = Image.new("RGB", (32, 32), color=(10, 200, 40))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_predict_multipart(client):
    """Accept multipart image upload predictions."""
    image_bytes = _make_image_bytes()
    resp = client.post(
        "/predict",
        data={"model_name": "model_a", "image": (io.BytesIO(image_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert 0 <= payload["top1_conf"] <= 1
    assert payload["latency_ms"] > 0


def test_predict_base64(client):
    """Accept base64 image payload predictions."""
    image_bytes = _make_image_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    resp = client.post(
        "/predict",
        json={"model_name": "model_b", "image_base64": encoded},
    )
    assert resp.status_code == 200


def test_predict_invalid_model(client):
    """Reject unknown model names."""
    image_bytes = _make_image_bytes()
    resp = client.post(
        "/predict",
        data={"model_name": "missing", "image": (io.BytesIO(image_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_predict_missing_image(client):
    """Reject requests without image payload."""
    resp = client.post("/predict", data={"model_name": "model_a"})
    assert resp.status_code == 400


def test_predict_requires_model_name(client):
    """Reject requests without model name."""
    image_bytes = _make_image_bytes()
    resp = client.post(
        "/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "validation_error"


def test_predict_rejects_invalid_base64(client):
    """Reject malformed base64 payloads."""
    resp = client.post(
        "/predict",
        json={"model_name": "model_a", "image_base64": "this-is-not-base64"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("raw_top_k", ["abc", "2.5", "", None])
def test_predict_top_k_must_be_integer(client, raw_top_k):
    """Validate that top_k is parsed as integer only."""
    image_bytes = _make_image_bytes()
    form_data = {"model_name": "model_a", "image": (io.BytesIO(image_bytes), "sample.png")}
    if raw_top_k is not None:
        form_data["top_k"] = raw_top_k
    resp = client.post(
        "/predict",
        data=form_data,
        content_type="multipart/form-data",
    )
    if raw_top_k is None:
        assert resp.status_code == 200
    else:
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("top_k", [0, 11])
def test_predict_top_k_out_of_range(client, top_k: int):
    """Reject top_k values outside supported range [1, 10]."""
    image_bytes = _make_image_bytes()
    resp = client.post(
        "/predict",
        data={
            "model_name": "model_a",
            "top_k": str(top_k),
            "image": (io.BytesIO(image_bytes), "sample.png"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "validation_error"
