"""Veggie API tests for catalog, prediction, detection, and history endpoints."""

from __future__ import annotations

import io

import pytest
import requests

from .conftest import make_image_bytes

pytestmark = [pytest.mark.api]


def _login(client):
    """Authenticate as admin and return JWT token."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.get_json()["data"]["token"]


def test_veggie_catalog_requires_auth(client):
    """Reject unauthenticated access to veggie catalog."""
    resp = client.get("/api/veggie/catalog")
    assert resp.status_code == 401


def test_veggie_catalog(client):
    """Return seeded vegetable catalog and pricing metadata."""
    token = _login(client)
    resp = client.get("/api/veggie/catalog", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert payload["vegetables"]
    assert "prices" in payload["vegetables"][0]


def test_veggie_prices_requires_auth(client):
    """Reject unauthenticated access to price endpoints."""
    resp = client.get("/api/veggie/prices")
    assert resp.status_code == 401


def test_veggie_prices_with_auth(client):
    """Return all vegetable prices for authenticated users."""
    token = _login(client)
    resp = client.get("/api/veggie/prices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert payload["vegetables"]


def test_veggie_models_requires_auth(client):
    """Reject unauthenticated model-list requests."""
    resp = client.get("/api/veggie/models")
    assert resp.status_code == 401


def test_veggie_models_with_auth(client):
    """Return both VegNet-23 and VegNet-101 model options."""
    token = _login(client)
    resp = client.get("/api/veggie/models", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    payload = resp.get_json()["data"]
    assert payload["models"]
    assert payload["default_model"] in {"vegnet-23", "vegnet-101"}


def test_veggie_predict_requires_auth(client):
    """Reject unauthenticated predictions."""
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_veggie_detect_requires_auth(client):
    """Reject unauthenticated detection calls."""
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/veggie/detect",
        data={"image": (io.BytesIO(image_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_veggie_detect_not_configured(client):
    """Return service unavailable when Roboflow is not configured."""
    token = _login(client)
    image_bytes = make_image_bytes()
    resp = client.post(
        "/api/veggie/detect",
        data={"image": (io.BytesIO(image_bytes), "sample.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 503


def test_veggie_detect_success_calls_roboflow(client, monkeypatch):
    """Call Roboflow endpoint and return the highest-confidence detection."""
    token = _login(client)
    client.application.config["ROBOFLOW_API_KEY"] = "rf-test-key"
    client.application.config["ROBOFLOW_MODEL_ID"] = "workspace/veg-model/3"

    image_bytes = make_image_bytes()
    captured: dict[str, object] = {}

    def _fake_post(url, params, files, timeout):
        """Capture Roboflow request payload and return deterministic detections."""
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        captured["files"] = files
        return _FakeResponse(
            200,
            {
                "predictions": [
                    {"class": "tomato", "confidence": 0.91, "x": 100, "y": 80, "width": 50, "height": 50},
                    {"class": "potato", "confidence": 0.42, "x": 20, "y": 30, "width": 10, "height": 15},
                ]
            },
        )

    monkeypatch.setattr("backend.veggie.requests.post", _fake_post)

    response = client.post(
        "/api/veggie/detect",
        data={"image": (io.BytesIO(image_bytes), "detect.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["detection"]["label"] == "tomato"
    assert payload["detection"]["confidence"] == 91.0
    assert payload["count"] == 2

    assert captured["url"] == "https://detect.roboflow.com/workspace/veg-model/3"
    assert captured["params"] == {"api_key": "rf-test-key"}
    assert captured["timeout"] == client.application.config["ROBOFLOW_TIMEOUT_SEC"]


def test_veggie_detect_success_calls_roboflow_workflow(client, monkeypatch):
    """Use workflow config when model ID is absent and return best prediction."""
    token = _login(client)
    client.application.config["ROBOFLOW_API_KEY"] = "rf-test-key"
    client.application.config["ROBOFLOW_MODEL_ID"] = ""
    client.application.config["ROBOFLOW_WORKSPACE"] = "gentle-care-messenger"
    client.application.config["ROBOFLOW_WORKFLOW_ID"] = "detect-count-and-visualize-5"
    client.application.config["ROBOFLOW_WORKFLOW_IMAGE_INPUT"] = "image"
    client.application.config["ROBOFLOW_BASE_URL"] = "https://detect.roboflow.com"

    image_bytes = make_image_bytes()
    captured: dict[str, object] = {}

    class _FakeWorkflowClient:
        """Minimal fake inference workflow client."""

        def run_workflow(self, workspace_name, workflow_id, images):
            captured["workspace_name"] = workspace_name
            captured["workflow_id"] = workflow_id
            captured["images"] = images
            return {
                "output": {
                    "predictions": [
                        {"class": "carrot", "confidence": 0.61, "x": 11, "y": 22, "width": 33, "height": 44},
                        {"class": "tomato", "confidence": 0.95, "x": 1, "y": 2, "width": 3, "height": 4},
                    ]
                }
            }

    class _FakeInferenceHTTPClient:
        """Fake inference client facade used by backend workflow mode."""

        @staticmethod
        def init(api_url, api_key):
            captured["api_url"] = api_url
            captured["api_key"] = api_key
            return _FakeWorkflowClient()

    monkeypatch.setattr("backend.veggie.InferenceHTTPClient", _FakeInferenceHTTPClient)

    response = client.post(
        "/api/veggie/detect",
        data={"image": (io.BytesIO(image_bytes), "detect.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["detection"]["label"] == "tomato"
    assert payload["detection"]["confidence"] == 95.0
    assert payload["count"] == 2

    assert captured["api_url"] == "https://detect.roboflow.com"
    assert captured["api_key"] == "rf-test-key"
    assert captured["workspace_name"] == "gentle-care-messenger"
    assert captured["workflow_id"] == "detect-count-and-visualize-5"
    images = captured["images"]
    assert isinstance(images, dict)
    assert "image" in images
    assert isinstance(images["image"], str)


def test_veggie_detect_workflow_requires_inference_sdk(client, monkeypatch):
    """Return 503 when workflow mode is configured but inference-sdk is unavailable."""
    token = _login(client)
    client.application.config["ROBOFLOW_API_KEY"] = "rf-test-key"
    client.application.config["ROBOFLOW_MODEL_ID"] = ""
    client.application.config["ROBOFLOW_WORKSPACE"] = "gentle-care-messenger"
    client.application.config["ROBOFLOW_WORKFLOW_ID"] = "detect-count-and-visualize-5"

    monkeypatch.setattr("backend.veggie.InferenceHTTPClient", None)

    image_bytes = make_image_bytes()
    response = client.post(
        "/api/veggie/detect",
        data={"image": (io.BytesIO(image_bytes), "detect.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "service_unavailable"


def test_veggie_detect_handles_roboflow_timeout(client, monkeypatch):
    """Return service-unavailable when Roboflow times out."""
    token = _login(client)
    client.application.config["ROBOFLOW_API_KEY"] = "rf-test-key"
    client.application.config["ROBOFLOW_MODEL_ID"] = "workspace/veg-model/3"
    image_bytes = make_image_bytes()

    def _raise_timeout(*args, **kwargs):
        """Raise timeout to emulate Roboflow outage."""
        raise requests.Timeout("timed out")

    monkeypatch.setattr("backend.veggie.requests.post", _raise_timeout)

    response = client.post(
        "/api/veggie/detect",
        data={"image": (io.BytesIO(image_bytes), "detect.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "service_unavailable"


def test_veggie_detect_handles_roboflow_http_error(client, monkeypatch):
    """Return service-error when Roboflow responds with a failing status."""
    token = _login(client)
    client.application.config["ROBOFLOW_API_KEY"] = "rf-test-key"
    client.application.config["ROBOFLOW_MODEL_ID"] = "workspace/veg-model/3"
    image_bytes = make_image_bytes()

    def _fake_error(*args, **kwargs):
        """Return upstream HTTP error response."""
        return _FakeResponse(429, {"error": "rate_limited"})

    monkeypatch.setattr("backend.veggie.requests.post", _fake_error)

    response = client.post(
        "/api/veggie/detect",
        data={"image": (io.BytesIO(image_bytes), "detect.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "service_error"


def test_veggie_predict_and_history(client):
    """Create prediction records and return user-scoped history entries."""
    token = _login(client)
    image_bytes = make_image_bytes()
    predict = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-101"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert predict.status_code == 201
    prediction = predict.get_json()["data"]["prediction"]
    assert prediction["vegetable"]
    assert prediction["modelName"] == "vegnet-101"
    assert 0 <= prediction["confidence"] <= 100

    history = client.get("/api/veggie/history", headers={"Authorization": f"Bearer {token}"})
    assert history.status_code == 200
    items = history.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == prediction["id"]


def test_veggie_predict_backfills_missing_catalog_class(client, monkeypatch):
    """Map model labels to normalized catalog keys when catalog rows are missing."""
    token = _login(client)
    image_bytes = make_image_bytes()

    with client.application.app_context():
        from backend.db import get_db

        db = get_db()
        db.execute("DELETE FROM vegetables WHERE key = ?", ("bitter_gourd",))
        db.commit()

    def _predict_bitter(*args, **kwargs):
        """Return deterministic Bitter_Gourd prediction for mapping tests."""
        return "Bitter_Gourd", 97.3

    monkeypatch.setattr("backend.veggie._predict_remote_vegetable", _predict_bitter)

    predict = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert predict.status_code == 201
    payload = predict.get_json()["data"]["prediction"]
    assert payload["key"] == "bitter_gourd"


def test_veggie_history_delete_and_clear(client):
    """Support deleting one item and clearing full veggie history."""
    token = _login(client)
    image_bytes = make_image_bytes()
    first = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    second = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample2.png")},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert first.status_code == 201
    assert second.status_code == 201

    prediction_id = first.get_json()["data"]["prediction"]["id"]
    delete_resp = client.delete(f"/api/veggie/history/{prediction_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_resp.status_code == 200

    clear_resp = client.delete("/api/veggie/history", headers={"Authorization": f"Bearer {token}"})
    assert clear_resp.status_code == 200
    assert clear_resp.get_json()["data"]["deleted"] >= 1


def test_veggie_history_image_returns_renderable_mime(client):
    """Serve history images with a concrete image MIME type."""
    token = _login(client)
    image_bytes = make_image_bytes()
    predict = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert predict.status_code == 201

    prediction_id = predict.get_json()["data"]["prediction"]["id"]
    image_response = client.get(
        f"/api/veggie/history/{prediction_id}/image",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert image_response.status_code == 200
    assert (image_response.headers.get("Content-Type") or "").startswith("image/")


def test_veggie_history_image_allows_session_authenticated_pages(client):
    """Allow image retrieval via Flask session auth for Jinja-rendered pages."""
    token = _login(client)
    image_bytes = make_image_bytes()
    predict = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert predict.status_code == 201

    prediction_id = predict.get_json()["data"]["prediction"]["id"]
    session_login = client.post("/web/session/login", json={"token": token})
    assert session_login.status_code == 200

    image_response = client.get(f"/api/veggie/history/{prediction_id}/image")
    assert image_response.status_code == 200
    assert (image_response.headers.get("Content-Type") or "").startswith("image/")


def test_veggie_history_image_supports_legacy_backend_upload_paths(client):
    """Resolve legacy refs that include a redundant ``backend/uploads`` prefix."""
    token = _login(client)
    image_bytes = make_image_bytes()
    predict = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert predict.status_code == 201

    prediction_id = predict.get_json()["data"]["prediction"]["id"]

    with client.application.app_context():
        from backend.db import get_db

        db = get_db()
        row = db.execute(
            "SELECT image_ref FROM veggie_predictions WHERE id = ?",
            (prediction_id,),
        ).fetchone()
        assert row
        legacy_ref = f"backend/uploads/{row['image_ref']}"
        db.execute(
            "UPDATE veggie_predictions SET image_ref = ? WHERE id = ?",
            (legacy_ref, prediction_id),
        )
        db.commit()

    image_response = client.get(
        f"/api/veggie/history/{prediction_id}/image",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert image_response.status_code == 200
    assert (image_response.headers.get("Content-Type") or "").startswith("image/")


def test_veggie_history_image_returns_404_when_file_disappears_before_send(client, monkeypatch):
    """Return 404 instead of 500 when history image disappears during send_file."""
    token = _login(client)
    predict = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(make_image_bytes()), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert predict.status_code == 201
    prediction_id = predict.get_json()["data"]["prediction"]["id"]

    def _raise_file_not_found(*_args, **_kwargs):
        raise FileNotFoundError("simulated race during send_file")

    monkeypatch.setattr("backend.veggie.send_file", _raise_file_not_found)
    image_response = client.get(
        f"/api/veggie/history/{prediction_id}/image",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert image_response.status_code == 404
    assert image_response.get_json()["error"]["code"] == "not_found"


def test_veggie_history_image_returns_404_on_send_os_error(client, monkeypatch):
    """Return 404 for OS-level send errors when reading stored history image."""
    token = _login(client)
    predict = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(make_image_bytes()), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert predict.status_code == 201
    prediction_id = predict.get_json()["data"]["prediction"]["id"]

    def _raise_os_error(*_args, **_kwargs):
        raise PermissionError("simulated permission denied")

    monkeypatch.setattr("backend.veggie.send_file", _raise_os_error)
    image_response = client.get(
        f"/api/veggie/history/{prediction_id}/image",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert image_response.status_code == 404
    assert image_response.get_json()["error"]["code"] == "not_found"


class _FakeResponse:
    """Simple fake response object used to mock remote model calls."""

    def __init__(self, status_code: int, payload: dict):
        """Initialize fake status and JSON payload."""
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        """Return fake JSON payload."""
        return self._payload


@pytest.mark.real_vegnet
def test_veggie_predict_calls_model_predict_endpoint(client, monkeypatch):
    """Send normalized 23x23x1 tensors to the selected model endpoint."""
    token = _login(client)
    image_bytes = make_image_bytes()
    called: dict[str, object] = {}

    scores = [0.0] * 11
    scores[10] = 0.98  # tomato

    def _fake_post(url, json, timeout):
        """Capture outbound payload and return a deterministic response."""
        called["url"] = url
        called["payload"] = json
        called["timeout"] = timeout
        return _FakeResponse(200, {"predictions": [scores]})

    monkeypatch.setattr("backend.veggie.requests.post", _fake_post)
    monkeypatch.setattr("backend.veggie.time.sleep", lambda *args, **kwargs: None)

    resp = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    assert called["url"] == "https://example.com/v1/models/vegnet-23:predict"
    sent_payload = called["payload"]
    assert isinstance(sent_payload, dict)
    assert "instances" in sent_payload
    assert len(sent_payload["instances"]) == 1
    instance = sent_payload["instances"][0]
    assert len(instance) == 23
    assert len(instance[0]) == 23
    assert len(instance[0][0]) == 1
    assert 0.0 <= instance[0][0][0] <= 1.0


def test_veggie_predict_remote_disabled_returns_503(client):
    """Return clear error when remote VegNet inference is disabled."""
    client.application.config["VEGNET_REMOTE_ENABLED"] = False
    token = _login(client)
    image_bytes = make_image_bytes()

    resp = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 503
    assert resp.get_json()["error"]["code"] == "model_service_disabled"


@pytest.mark.real_vegnet
def test_veggie_predict_remote_unreachable_returns_503(client, monkeypatch):
    """Return service-unavailable on remote timeout."""
    token = _login(client)
    image_bytes = make_image_bytes()

    def _raise_timeout(*args, **kwargs):
        """Raise timeout to simulate remote inference outage."""
        raise requests.Timeout("timed out")

    monkeypatch.setattr("backend.veggie.requests.post", _raise_timeout)

    resp = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 503
    assert resp.get_json()["error"]["code"] == "model_service_unavailable"


@pytest.mark.real_vegnet
def test_veggie_predict_invalid_remote_response_returns_502(client, monkeypatch):
    """Return bad-gateway on malformed remote response payload."""
    token = _login(client)
    image_bytes = make_image_bytes()

    def _bad_payload(*args, **kwargs):
        """Return malformed response payload."""
        return _FakeResponse(200, {"unexpected": "shape"})

    monkeypatch.setattr("backend.veggie.requests.post", _bad_payload)

    resp = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-23"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 502
    assert resp.get_json()["error"]["code"] == "model_response_invalid"
