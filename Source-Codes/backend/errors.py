"""Centralized Flask error handlers."""

import logging

from flask import current_app
from werkzeug.exceptions import HTTPException

from .utils.responses import error_response

logger = logging.getLogger(__name__)


def register_error_handlers(app) -> None:
    """Register HTTP and unexpected error handlers for the Flask app."""

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Return a normalized JSON payload for HTTP errors."""
        return error_response(
            "http_error",
            error.description,
            status=error.code or 400,
            details={"name": error.name},
        )

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        """Return a safe JSON payload for unexpected server exceptions."""
        logger.exception("Unhandled error")
        details = None
        if current_app.config.get("DEBUG") or current_app.config.get("TESTING"):
            details = str(error)
        return error_response("internal_error", "Unexpected server error", status=500, details=details)
