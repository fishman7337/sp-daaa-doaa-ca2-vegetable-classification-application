"""JSON response helpers for consistent API responses."""

from flask import g, jsonify


def ok_response(data: dict, status: int = 200):
    """Execute ok response."""
    return jsonify({"data": data, "request_id": getattr(g, "request_id", None)}), status


def error_response(code: str, message: str, status: int = 400, details=None):
    """Execute error response."""
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "request_id": getattr(g, "request_id", None),
    }
    return jsonify(payload), status
