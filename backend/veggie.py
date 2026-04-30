"""VeggieAI-compatible API routes backed by SQLite."""

from __future__ import annotations

import io
import logging
import mimetypes
import tempfile
import time
import uuid
from pathlib import Path

import requests
from flask import Blueprint, current_app, g, request, send_file
from PIL import Image, ImageOps

try:
    from inference_sdk import InferenceHTTPClient
except ImportError:  # pragma: no cover - dependency is optional in some environments
    InferenceHTTPClient = None

from .db import get_db
from .repository import (
    clear_veggie_predictions,
    delete_veggie_prediction,
    get_vegetable_by_key,
    get_veggie_prediction,
    insert_veggie_prediction,
    list_vegetables,
    list_veggie_predictions,
    seed_vegetables,
)
from .utils.files import resolve_uploaded_file_path
from .utils.jwt import jwt_required
from .utils.responses import error_response, ok_response
from .utils.validation import read_image_bytes
from .veggie_catalog import normalize_vegetable_key

logger = logging.getLogger(__name__)

veggie_bp = Blueprint("veggie", __name__, url_prefix="/api/veggie")

MODEL_CLASSES = [
    "Bean",
    "Bitter_Gourd",
    "Brinjal",
    "Cabbage",
    "Capsicum",
    "Cauliflower and Broccoli",
    "Cucumber and Bottle_Gourd",
    "Potato",
    "Pumpkin",
    "Radish and Carrot",
    "Tomato",
]

MODEL_LABEL_TO_KEY = {
    "bean": "bean",
    "bitter gourd": "bitter_gourd",
    "brinjal": "brinjal",
    "cabbage": "cabbage",
    "capsicum": "capsicum",
    "cauliflower and broccoli": "cauliflower_and_broccoli",
    "cucumber and bottle gourd": "cucumber_and_bottle_gourd",
    "potato": "potato",
    "pumpkin": "pumpkin",
    "radish and carrot": "radish_and_carrot",
    "tomato": "tomato",
}
MODEL_INPUT_SIZES = {
    "vegnet-23": 23,
    "vegnet-101": 101,
}
RESAMPLE_LOOKUP = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


def _parse_int(value: str | None, default: int) -> int:
    """Parse an integer query value with fallback to ``default``."""
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _resolve_image_mimetype(file_path: Path) -> str:
    """Resolve a concrete image MIME type for `send_file` with `nosniff` enabled."""
    guessed, _ = mimetypes.guess_type(file_path.name)
    if isinstance(guessed, str) and guessed.startswith("image/"):
        return guessed
    return "image/jpeg"


def _hydrate_image_url(item: dict) -> dict:
    """Attach the authenticated image endpoint URL to a history payload."""
    item["image"] = f"/api/veggie/history/{item['id']}/image"
    return item


def _veggie_models() -> list[dict]:
    """Return VegNet model options displayed in the UI model switcher."""
    return [
        {
            "name": "vegnet-23",
            "label": "VegNet-23 (23x23)",
            "inputSize": "23x23",
            "endpoint": current_app.config.get("VEGNET_23_URL", ""),
        },
        {
            "name": "vegnet-101",
            "label": "VegNet-101 (101x101)",
            "inputSize": "101x101",
            "endpoint": current_app.config.get("VEGNET_101_URL", ""),
        },
    ]


def _model_map() -> dict[str, dict]:
    """Return model metadata keyed by model name."""
    return {item["name"]: item for item in _veggie_models()}


def _normalize_model_label(value: str) -> str:
    """Normalize model labels to a canonical lowercase format."""
    return " ".join((value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _predict_endpoint(model_endpoint: str) -> str:
    """Return a TensorFlow Serving ``:predict`` endpoint URL."""
    endpoint = model_endpoint.strip().rstrip("/")
    if endpoint.endswith(":predict"):
        return endpoint
    return f"{endpoint}:predict"


def _parse_input_size(value: str) -> int:
    """Parse model input size from strings like ``23x23`` or ``101x101``."""
    raw = (value or "").split("x", maxsplit=1)[0].strip()
    try:
        size = int(raw)
    except ValueError:
        return 23
    if size <= 0:
        return 23
    return size


def _resolve_model_input_size(model_name: str, configured_value: str | None = None) -> int:
    """Resolve input tensor size for a model, enforcing VegNet defaults.

    For known VegNet models, this function always returns the canonical size:
    - ``vegnet-23`` -> ``23``
    - ``vegnet-101`` -> ``101``
    """
    normalized_name = (model_name or "").strip().lower()
    if normalized_name in MODEL_INPUT_SIZES:
        return MODEL_INPUT_SIZES[normalized_name]
    return _parse_input_size(configured_value or "23")


def _resolve_resize_strategy(model_name: str, input_size: int):
    """Resolve the PIL resize strategy for a VegNet model.

    VegNet-23 is highly sensitive to interpolation artifacts due to aggressive
    downsampling. ``nearest`` preserves class features better for 23x23 input.
    """
    normalized_name = (model_name or "").strip().lower()
    config_key = {
        "vegnet-23": "VEGNET_23_RESAMPLE",
        "vegnet-101": "VEGNET_101_RESAMPLE",
    }.get(normalized_name)

    configured = ""
    if config_key:
        configured = str(current_app.config.get(config_key) or "").strip().lower()
    if configured in RESAMPLE_LOOKUP:
        return RESAMPLE_LOOKUP[configured]

    # Safe defaults when env vars are omitted.
    if normalized_name == "vegnet-23" or input_size <= 32:
        return Image.Resampling.NEAREST
    return Image.Resampling.BICUBIC


def _preprocess_image_for_tf_serving(image_bytes: bytes, input_size: int, model_name: str) -> list[list[list[float]]]:
    """Convert an input image into the normalized tensor expected by VegNet."""
    resize_strategy = _resolve_resize_strategy(model_name=model_name, input_size=input_size)
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image = ImageOps.grayscale(image)
        image = image.resize((input_size, input_size), resample=resize_strategy)
        pixels = list(image.getdata())

    rows: list[list[list[float]]] = []
    index = 0
    for _ in range(input_size):
        row: list[list[float]] = []
        for _ in range(input_size):
            row.append([float(pixels[index]) / 255.0])
            index += 1
        rows.append(row)
    return rows


def _request_with_retry(url: str, payload: dict, timeout: int, retries: int):
    """Call a remote endpoint with bounded retry/backoff semantics."""
    backoff = 0.5
    attempts = max(0, retries) + 1
    for attempt in range(attempts):
        try:
            response = requests.post(url, json=payload, timeout=timeout)
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 4.0)
            continue

        if response.status_code in {502, 503, 504} and attempt < attempts - 1:
            time.sleep(backoff)
            backoff = min(backoff * 2, 4.0)
            continue
        return response

    raise requests.RequestException("Remote model request failed after retries")


def _extract_probability_vector(response_payload: dict) -> list[float]:
    """Extract a flat probability vector from TensorFlow Serving responses."""
    predictions = response_payload.get("predictions")
    if not isinstance(predictions, list) or not predictions:
        raise ValueError("Missing predictions in model response")

    first = predictions[0]
    if isinstance(first, dict):
        if "dense_1" in first:
            raw_scores = first["dense_1"]
        else:
            raw_scores = next((value for value in first.values() if isinstance(value, list)), None)
    else:
        raw_scores = first

    if not isinstance(raw_scores, list) or not raw_scores:
        raise ValueError("Model response did not contain a probability vector")

    try:
        scores = [float(value) for value in raw_scores]
    except (TypeError, ValueError) as exc:
        raise ValueError("Model response contained non-numeric scores") from exc
    return scores


def _predict_remote_vegetable(model_name: str, endpoint: str, image_bytes: bytes, input_size: int) -> tuple[str, float]:
    """Call the selected VegNet model and return top-1 class and confidence."""
    timeout = max(int(current_app.config.get("VEGNET_REMOTE_TIMEOUT_SEC", 8)), 1)
    retries = max(int(current_app.config.get("VEGNET_REMOTE_RETRIES", 1)), 0)

    payload = {
        "instances": [_preprocess_image_for_tf_serving(image_bytes, input_size, model_name=model_name)],
    }
    response = _request_with_retry(_predict_endpoint(endpoint), payload, timeout, retries)
    if response.status_code >= 400:
        details = ""
        try:
            details = response.text[:300]
        except Exception:
            details = ""
        raise ValueError(f"Model endpoint returned status {response.status_code}: {details}")

    try:
        body = response.json()
    except ValueError as exc:
        raise ValueError("Model response was not valid JSON") from exc
    scores = _extract_probability_vector(body)
    if len(scores) != len(MODEL_CLASSES):
        raise ValueError(f"Model returned {len(scores)} scores, expected {len(MODEL_CLASSES)}")

    top_index = max(range(len(MODEL_CLASSES)), key=lambda idx: scores[idx])
    confidence = float(scores[top_index])
    if confidence <= 1:
        confidence *= 100.0
    confidence = max(0.0, min(100.0, confidence))
    return MODEL_CLASSES[top_index], round(confidence, 1)


@veggie_bp.get("/catalog")
@jwt_required
def catalog():
    """Return the vegetable catalog and price details."""
    db = get_db()
    seed_vegetables(db)
    items = list_vegetables(db)
    return ok_response({"vegetables": items})


@veggie_bp.get("/models")
@jwt_required
def veggie_models():
    """Return available VegNet model options for UI switching."""
    models = _veggie_models()
    default_model = current_app.config.get("VEGGIE_DEFAULT_MODEL", "vegnet-23")
    if default_model not in {item["name"] for item in models}:
        default_model = "vegnet-23"
    return ok_response({"models": models, "default_model": default_model})


@veggie_bp.get("/prices")
@jwt_required
def prices():
    """Return all prices or a single vegetable by key/name."""
    db = get_db()
    seed_vegetables(db)
    key = normalize_vegetable_key(request.args.get("vegetable", ""))
    if key:
        item = get_vegetable_by_key(db, key)
        if not item:
            return error_response("not_found", "Vegetable not found", status=404)
        return ok_response({"vegetable": item})
    return ok_response({"vegetables": list_vegetables(db)})


@veggie_bp.post("/predict")
@jwt_required
def veggie_predict():
    """Predict a vegetable label using remote VegNet and persist to SQLite."""
    file_storage = request.files.get("image")
    try:
        image_bytes, ext, image_sha256 = read_image_bytes(file_storage)
    except ValueError as exc:
        return error_response("invalid_image", "Invalid image upload", details=str(exc))

    db = get_db()
    seed_vegetables(db)

    model_name = (request.form.get("model_name") or current_app.config.get("VEGGIE_DEFAULT_MODEL", "vegnet-23")).strip()
    models = _model_map()
    selected_model = models.get(model_name)
    if not selected_model:
        return error_response("unsupported_model", "Model not found", status=400)
    if not bool(current_app.config.get("VEGNET_REMOTE_ENABLED", True)):
        return error_response("model_service_disabled", "Remote model inference is disabled", status=503)

    endpoint = (selected_model.get("endpoint") or "").strip()
    if not endpoint:
        return error_response("model_not_configured", "Selected model endpoint is not configured", status=503)

    try:
        predicted_label, confidence = _predict_remote_vegetable(
            model_name=model_name,
            endpoint=endpoint,
            image_bytes=image_bytes,
            input_size=_resolve_model_input_size(model_name, str(selected_model.get("inputSize") or "23")),
        )
    except requests.RequestException as exc:
        logger.warning("remote_model_unreachable model=%s error=%s", model_name, str(exc))
        return error_response("model_service_unavailable", "Selected model endpoint is unavailable", status=503)
    except ValueError as exc:
        logger.warning("remote_model_invalid_response model=%s error=%s", model_name, str(exc))
        return error_response("model_response_invalid", "Selected model returned an invalid response", status=502)

    normalized_label = _normalize_model_label(predicted_label)
    vegetable_key = MODEL_LABEL_TO_KEY.get(normalized_label) or normalize_vegetable_key(predicted_label)
    vegetable = get_vegetable_by_key(db, vegetable_key)
    if not vegetable:
        return error_response(
            "model_label_unmapped",
            "Predicted vegetable is not configured in the catalog",
            details={"label": predicted_label},
            status=500,
        )

    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{image_sha256}.{ext}"
    file_path = upload_dir / filename
    if not file_path.exists():
        file_path.write_bytes(image_bytes)

    prediction_id = str(uuid.uuid4())
    insert_veggie_prediction(
        db,
        prediction_id=prediction_id,
        user_id=int(g.user["sub"]),
        image_ref=filename,
        image_sha256=image_sha256,
        model_name=model_name,
        vegetable_key=vegetable_key,
        confidence=confidence,
    )

    row = get_veggie_prediction(db, int(g.user["sub"]), prediction_id)
    if not row:
        return error_response("server_error", "Prediction could not be stored", status=500)
    payload = _hydrate_image_url(row)
    return ok_response({"prediction": payload}, status=201)


@veggie_bp.post("/detect")
@jwt_required
def veggie_detect():
    """Run camera-style object detection through Roboflow and return top prediction."""
    file_storage = request.files.get("image")
    try:
        image_bytes, _, _ = read_image_bytes(file_storage)
    except ValueError as exc:
        return error_response("invalid_image", "Invalid image upload", details=str(exc))

    api_key = (current_app.config.get("ROBOFLOW_API_KEY", "") or "").strip()
    model_id = (request.form.get("model_id") or current_app.config.get("ROBOFLOW_MODEL_ID", "")).strip()
    workspace = (
        request.form.get("workspace_name")
        or request.form.get("workspace")
        or current_app.config.get("ROBOFLOW_WORKSPACE", "")
    ).strip()
    workflow_id = (
        request.form.get("workflow_id")
        or request.form.get("workflow")
        or current_app.config.get("ROBOFLOW_WORKFLOW_ID", "")
    ).strip()
    image_input = (
        request.form.get("image_input") or current_app.config.get("ROBOFLOW_WORKFLOW_IMAGE_INPUT", "image")
    ).strip() or "image"
    base_url = (current_app.config.get("ROBOFLOW_BASE_URL", "") or "").strip() or "https://detect.roboflow.com"
    base_url = base_url.rstrip("/")
    timeout_sec = int(current_app.config.get("ROBOFLOW_TIMEOUT_SEC", 10))

    has_model_config = bool(model_id)
    has_workflow_config = bool(workspace and workflow_id)
    if not api_key or (not has_model_config and not has_workflow_config):
        return error_response(
            "service_unavailable",
            "Roboflow detection is not configured. Set ROBOFLOW_MODEL_ID or ROBOFLOW_WORKSPACE + ROBOFLOW_WORKFLOW_ID.",
            status=503,
        )

    payload: object
    if has_model_config:
        try:
            response = requests.post(
                f"{base_url}/{model_id}",
                params={"api_key": api_key},
                files={"file": ("frame.jpg", image_bytes, "image/jpeg")},
                timeout=timeout_sec,
            )
        except requests.RequestException as exc:
            return error_response(
                "service_unavailable", "Roboflow service is unavailable", details=str(exc), status=503
            )

        if response.status_code >= 400:
            details = response.text
            try:
                details = response.json()
            except ValueError:
                pass
            return error_response("service_error", "Roboflow request failed", details=details, status=502)

        try:
            payload = response.json()
        except ValueError:
            return error_response("service_error", "Invalid Roboflow response", status=502)
    else:
        if InferenceHTTPClient is None:
            return error_response(
                "service_unavailable",
                "Workflow detection requires the optional 'inference-sdk' package. Install backend dependencies and restart.",
                status=503,
            )

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="rf-detect-", suffix=".jpg", delete=False) as handle:
                handle.write(image_bytes)
                temp_path = Path(handle.name)

            client = InferenceHTTPClient.init(api_url=base_url, api_key=api_key)
            payload = client.run_workflow(
                workspace_name=workspace,
                workflow_id=workflow_id,
                images={image_input: str(temp_path)},
            )
        except Exception as exc:
            return error_response(
                "service_unavailable",
                "Roboflow workflow service is unavailable",
                details=str(exc),
                status=503,
            )
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    predictions: list[dict] = []
    stack: list[object] = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            has_confidence = "confidence" in node
            has_label = "class" in node or "label" in node
            has_box = any(key in node for key in ("x", "y", "width", "height", "box"))
            if has_confidence and (has_label or has_box):
                predictions.append(node)
            for value in node.values():
                stack.append(value)
        elif isinstance(node, list):
            for value in node:
                stack.append(value)

    threshold = float(current_app.config.get("ROBOFLOW_CONFIDENCE_THRESHOLD", 0.35))
    threshold_percent = threshold * 100.0 if threshold <= 1 else threshold
    best: dict | None = None
    best_confidence = -1.0
    for item in predictions:
        raw_confidence = item.get("confidence")
        try:
            confidence = float(raw_confidence or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence_percent = confidence * 100.0 if confidence <= 1 else confidence
        if confidence_percent < threshold_percent or confidence_percent <= best_confidence:
            continue
        best = item
        best_confidence = confidence_percent

    if not best:
        return ok_response({"detection": None, "count": len(predictions)})

    box = best.get("box") if isinstance(best.get("box"), dict) else {}
    return ok_response(
        {
            "detection": {
                "label": best.get("class") or best.get("label") or "",
                "confidence": round(best_confidence, 1),
                "box": {
                    "x": box.get("x", best.get("x")),
                    "y": box.get("y", best.get("y")),
                    "width": box.get("width", best.get("width")),
                    "height": box.get("height", best.get("height")),
                },
            },
            "count": len(predictions),
        }
    )


@veggie_bp.get("/history")
@jwt_required
def veggie_history():
    """List user prediction history in UI-friendly shape."""
    page = max(_parse_int(request.args.get("page"), 1), 1)
    page_size = _parse_int(request.args.get("page_size"), 20)
    if page_size < 1 or page_size > 100:
        return error_response("validation_error", "page_size must be 1-100")

    db = get_db()
    items, total = list_veggie_predictions(db, int(g.user["sub"]), page, page_size)
    items = [_hydrate_image_url(item) for item in items]
    pages = max((total + page_size - 1) // page_size, 1)
    return ok_response(
        {
            "items": items,
            "page": {"page": page, "page_size": page_size, "total": total, "pages": pages},
        }
    )


@veggie_bp.get("/history/<string:prediction_id>")
@jwt_required
def veggie_history_item(prediction_id: str):
    """Return one history record for the authenticated user."""
    row = get_veggie_prediction(get_db(), int(g.user["sub"]), prediction_id)
    if not row:
        return error_response("not_found", "Prediction not found", status=404)
    return ok_response(_hydrate_image_url(row))


@veggie_bp.get("/history/<string:prediction_id>/image")
@jwt_required(allow_query_token=True, allow_session_user=True)
def veggie_history_image(prediction_id: str):
    """Serve stored image for one veggie prediction."""
    row = get_veggie_prediction(get_db(), int(g.user["sub"]), prediction_id)
    if not row:
        return error_response("not_found", "Prediction not found", status=404)

    uploads_dir = Path(current_app.config["UPLOAD_DIR"])
    file_path = resolve_uploaded_file_path(uploads_dir, row.get("imageRef"))
    if not file_path:
        return error_response("not_found", "Image not found", status=404)
    try:
        return send_file(file_path, mimetype=_resolve_image_mimetype(file_path))
    except FileNotFoundError:
        return error_response("not_found", "Image not found", status=404)
    except OSError:
        return error_response("not_found", "Image not found", status=404)


@veggie_bp.delete("/history/<string:prediction_id>")
@jwt_required
def veggie_delete_history_item(prediction_id: str):
    """Delete one history record."""
    deleted = delete_veggie_prediction(get_db(), int(g.user["sub"]), prediction_id)
    if not deleted:
        return error_response("not_found", "Prediction not found", status=404)
    return ok_response({"deleted": True, "id": prediction_id})


@veggie_bp.delete("/history")
@jwt_required
def veggie_clear_history():
    """Delete all history records for the current user."""
    deleted = clear_veggie_predictions(get_db(), int(g.user["sub"]))
    return ok_response({"deleted": deleted})
