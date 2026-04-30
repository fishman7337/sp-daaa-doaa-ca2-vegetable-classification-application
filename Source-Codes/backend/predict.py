"""Prediction routes for model inference."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests
from flask import Blueprint, current_app, g, request
from werkzeug.datastructures import CombinedMultiDict

from .db import get_db
from .forms import PredictForm
from .repository import insert_prediction
from .utils.jwt import jwt_required
from .utils.logging import log_event
from .utils.models_config import load_models_config, model_names
from .utils.responses import error_response, ok_response
from .utils.validation import read_image_bytes

logger = logging.getLogger(__name__)

predict_bp = Blueprint("predict", __name__, url_prefix="/api")


@predict_bp.get("/models")
def list_models():
    """List available models and labels."""
    models = load_models_config(current_app.config["MODELS_ROOT"])
    return ok_response({"models": models})


@predict_bp.post("/predict")
@jwt_required
def predict():
    """Validate input, call model service, and store prediction."""
    form = PredictForm(formdata=CombinedMultiDict([request.form, request.files]))
    if not form.validate():
        return error_response("validation_error", "Invalid prediction payload", details=form.errors)

    model_name = (form.model_name.data or "").strip()

    models_root = current_app.config["MODELS_ROOT"]
    if model_name not in model_names(models_root):
        return error_response("unsupported_model", "Model not found", status=400)

    file_storage = form.image.data
    try:
        image_bytes, ext, sha256 = read_image_bytes(file_storage)
    except ValueError as exc:
        return error_response("invalid_image", "Invalid image upload", details=str(exc))

    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{sha256}.{ext}"
    file_path = upload_dir / filename
    if not file_path.exists():
        file_path.write_bytes(image_bytes)

    input_type = request.form.get("input_type", "upload")
    notes = (form.notes.data or "").strip() or None

    try:
        response = requests.post(
            f"{current_app.config['MODEL_SERVICE_URL'].rstrip('/')}/predict",
            files={"image": (filename, image_bytes)},
            data={"model_name": model_name},
            timeout=current_app.config["MODEL_SERVICE_TIMEOUT_SEC"],
        )
    except requests.RequestException as exc:
        log_event(logger, "model_service_unreachable", error=str(exc))
        return error_response("model_service_unavailable", "Model service unavailable", status=503)

    if response.status_code != 200:
        try:
            payload = response.json()
        except ValueError:
            payload = {"message": response.text}
        return error_response("model_service_error", "Model service error", status=502, details=payload)

    try:
        payload = response.json()
    except ValueError:
        return error_response("model_service_error", "Invalid response from model service", status=502)

    prediction = payload.get("data") or payload
    if not prediction:
        return error_response("model_service_error", "Malformed model response", status=502)
    required_keys = {"top1_label", "top1_conf", "topk", "latency_ms"}
    if not required_keys.issubset(prediction.keys()):
        return error_response("model_service_error", "Incomplete model response", status=502)

    record_id = insert_prediction(
        get_db(),
        {
            "user_id": g.user["sub"],
            "model_name": model_name,
            "input_type": input_type,
            "input_ref": filename,
            "sha256": sha256,
            "top1_label": prediction.get("top1_label"),
            "top1_conf": prediction.get("top1_conf"),
            "topk_json": json.dumps(prediction.get("topk", [])),
            "latency_ms": prediction.get("latency_ms"),
            "notes": notes,
        },
    )

    log_event(logger, "prediction_stored", prediction_id=record_id, model=model_name)
    return ok_response(
        {
            "history_id": record_id,
            "prediction": prediction,
            "sha256": sha256,
        },
        status=201,
    )
