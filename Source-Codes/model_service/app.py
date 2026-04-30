"""Flask app for model inference service."""

from __future__ import annotations

import base64
import logging
import os
import uuid

from flask import Flask, g, request

from .config import load_settings
from .models import ModelRegistry
from .utils.logging import configure_logging
from .utils.responses import error_response, ok_response

logger = logging.getLogger(__name__)


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the model service application.

    Args:
        test_config: Optional configuration overrides for test execution.

    Returns:
        Flask: Configured model-service Flask application.
    """
    app = Flask(__name__)
    settings = load_settings()
    app.config.from_mapping(settings.to_dict())
    if test_config:
        app.config.update(test_config)
    app.config["JSON_SORT_KEYS"] = False

    configure_logging(app.config.get("LOG_LEVEL", "INFO"))

    registry = ModelRegistry(app.config["MODELS_ROOT"], app.config["MODEL_MODE"])
    registry.load()
    app.config["MODEL_REGISTRY"] = registry

    @app.before_request
    def assign_request_id():
        """Execute assign request id."""
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def attach_request_id(response):
        """Execute attach request id."""
        response.headers["X-Request-ID"] = g.get("request_id", "")
        return response

    @app.get("/health")
    def health():
        """Execute health."""
        return ok_response({"status": "ok", "models": registry.list_models()})

    @app.post("/predict")
    def predict():
        """Execute predict."""
        model_name = request.form.get("model_name")
        payload = request.get_json(silent=True) or {}
        if not model_name:
            model_name = payload.get("model_name")
        if not model_name:
            return error_response("validation_error", "model_name is required")

        try:
            top_k = int(request.form.get("top_k", payload.get("top_k", app.config["DEFAULT_TOP_K"])))
        except (ValueError, TypeError):
            return error_response("validation_error", "top_k must be an integer")
        if top_k < 1 or top_k > 10:
            return error_response("validation_error", "top_k must be between 1 and 10")

        image_bytes = None
        if "image" in request.files:
            image_bytes = request.files["image"].read()
        elif payload.get("image_base64"):
            try:
                image_bytes = base64.b64decode(payload["image_base64"])
            except (ValueError, TypeError):
                return error_response("validation_error", "Invalid base64 image")

        if not image_bytes:
            return error_response("validation_error", "image is required")

        model = registry.get(model_name)
        if not model:
            return error_response("unsupported_model", "Model not found", status=400)

        result = model.predict(image_bytes, top_k)
        return ok_response(result)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
