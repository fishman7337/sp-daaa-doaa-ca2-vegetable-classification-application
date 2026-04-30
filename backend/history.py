"""History routes for searching and retrieving predictions."""

from __future__ import annotations

import logging
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, g, request, send_file

from .db import get_db
from .repository import delete_prediction, get_prediction_by_id, search_predictions
from .utils.files import resolve_uploaded_file_path
from .utils.jwt import jwt_required
from .utils.responses import error_response, ok_response

logger = logging.getLogger(__name__)

history_bp = Blueprint("history", __name__, url_prefix="/api")


def _parse_int(value: str | None, default: int) -> int:
    """Parse an integer query parameter with a default fallback."""
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


@history_bp.get("/history")
@jwt_required
def list_history():
    """Return paginated prediction history with search and filters."""
    page = max(_parse_int(request.args.get("page"), 1), 1)
    page_size = _parse_int(request.args.get("page_size"), 10)
    if page_size < 1 or page_size > 100:
        return error_response("validation_error", "page_size must be 1-100")

    sort = request.args.get("sort", "newest")
    filters = {
        "model": request.args.get("model"),
        "label": request.args.get("label"),
        "user": request.args.get("user"),
    }

    date_from = request.args.get("date_from")
    if date_from:
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            filters["date_from"] = date_from
        except ValueError:
            return error_response("validation_error", "date_from must be YYYY-MM-DD")
    date_to = request.args.get("date_to")
    if date_to:
        try:
            end = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            filters["date_to"] = end.strftime("%Y-%m-%d")
        except ValueError:
            return error_response("validation_error", "date_to must be YYYY-MM-DD")

    if request.args.get("conf_min"):
        try:
            filters["conf_min"] = float(request.args.get("conf_min"))
        except ValueError:
            return error_response("validation_error", "conf_min must be a number")
    if request.args.get("conf_max"):
        try:
            filters["conf_max"] = float(request.args.get("conf_max"))
        except ValueError:
            return error_response("validation_error", "conf_max must be a number")
    if request.args.get("latency_max"):
        try:
            filters["latency_max"] = float(request.args.get("latency_max"))
        except ValueError:
            return error_response("validation_error", "latency_max must be a number")

    search_text = request.args.get("q", "")

    user_id = int(g.user["sub"])
    rows, total = search_predictions(get_db(), user_id, search_text, filters, page, page_size, sort)
    for row in rows:
        row["image_url"] = f"/api/history/{row['id']}/image"
    pages = max((total + page_size - 1) // page_size, 1)
    return ok_response(
        {
            "items": rows,
            "page": {"page": page, "page_size": page_size, "total": total, "pages": pages},
        }
    )


@history_bp.get("/history/<int:prediction_id>")
@jwt_required
def get_history(prediction_id: int):
    """Return a single prediction record by ID."""
    row = get_prediction_by_id(get_db(), prediction_id, int(g.user["sub"]))
    if not row:
        return error_response("not_found", "Prediction not found", status=404)
    row["image_url"] = f"/api/history/{row['id']}/image"
    return ok_response(row)


@history_bp.get("/history/<int:prediction_id>/image")
@jwt_required(allow_query_token=True)
def get_history_image(prediction_id: int):
    """Serve the stored input image for a prediction."""
    row = get_prediction_by_id(get_db(), prediction_id, int(g.user["sub"]))
    if not row:
        return error_response("not_found", "Prediction not found", status=404)
    uploads_dir = Path(current_app.config["UPLOAD_DIR"])
    file_path = resolve_uploaded_file_path(uploads_dir, row.get("input_ref"))
    if not file_path:
        return error_response("not_found", "Image not found", status=404)
    try:
        return send_file(file_path, mimetype=_resolve_image_mimetype(file_path))
    except FileNotFoundError:
        return error_response("not_found", "Image not found", status=404)
    except OSError:
        return error_response("not_found", "Image not found", status=404)


@history_bp.delete("/history/<int:prediction_id>")
@jwt_required
def remove_history(prediction_id: int):
    """Delete a prediction record by ID."""
    user_id = int(g.user["sub"])
    row = get_prediction_by_id(get_db(), prediction_id, user_id)
    if not row:
        return error_response("not_found", "Prediction not found", status=404)
    delete_prediction(get_db(), prediction_id, user_id)
    return ok_response({"deleted": True})
