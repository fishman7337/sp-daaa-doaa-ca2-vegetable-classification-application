"""Flask application factory for the backend service."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, redirect, request, session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .auth import auth_bp
from .chat import chat_bp
from .config import load_settings
from .db import close_db, get_db, init_db
from .errors import register_error_handlers
from .history import history_bp
from .predict import predict_bp
from .repository import seed_vegetables
from .utils.logging import configure_logging
from .utils.models_config import load_models_config
from .utils.responses import ok_response
from .utils.security import seed_admin
from .veggie import veggie_bp
from .views import views_bp

logger = logging.getLogger(__name__)


def _ensure_blob_img_src(csp_policy: str) -> str:
    """Ensure CSP `img-src` directive allows `blob:` previews."""
    policy = (csp_policy or "").strip()
    if not policy:
        return "default-src 'self'; img-src 'self' data: blob: https:"

    directives = [directive.strip() for directive in policy.split(";") if directive.strip()]
    for index, directive in enumerate(directives):
        if not directive.startswith("img-src"):
            continue
        parts = directive.split()
        if "blob:" not in parts:
            parts.append("blob:")
        directives[index] = " ".join(parts)
        break
    else:
        directives.append("img-src 'self' data: blob: https:")

    return "; ".join(directives)


def _resolve_frontend_paths() -> tuple[str, str]:
    """Resolve template and static directories for the Jinja frontend.

    Returns:
        tuple[str, str]: Absolute paths for `(template_folder, static_folder)`.
    """
    repo_root = Path(__file__).resolve().parents[1]
    template_dir = repo_root / "webapp" / "app" / "templates"
    static_dir = repo_root / "webapp" / "app" / "static"

    if not template_dir.exists() or not static_dir.exists():
        raise FileNotFoundError(f"Frontend assets are missing. Expected directories: {template_dir} and {static_dir}")

    return str(template_dir), str(static_dir)


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the backend Flask application.

    Args:
        test_config: Optional configuration overrides for tests.

    Returns:
        Flask: Configured Flask application instance.
    """
    template_folder, static_folder = _resolve_frontend_paths()
    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder,
        static_url_path="/static",
    )
    settings = load_settings()
    app.config.from_mapping(settings.to_dict())
    if test_config:
        app.config.update(test_config)
    app.config["JSON_SORT_KEYS"] = False
    app.secret_key = app.config["SECRET_KEY"]
    app.config["SESSION_COOKIE_HTTPONLY"] = bool(app.config.get("SESSION_COOKIE_HTTPONLY", True))
    app.config["SESSION_COOKIE_SECURE"] = bool(app.config.get("SESSION_COOKIE_SECURE", False))
    app.config["SESSION_COOKIE_SAMESITE"] = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")

    # Trust the first reverse-proxy hop (Render) so URL generation and scheme-sensitive
    # logic resolve to the external HTTPS request instead of internal HTTP.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    configure_logging(app.config.get("LOG_LEVEL", "INFO"))
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}},
        supports_credentials=True,
    )
    register_error_handlers(app)
    app.teardown_appcontext(close_db)

    @app.before_request
    def enforce_https():
        """Redirect plain HTTP requests to HTTPS when enabled."""
        if app.config.get("TESTING") or not app.config.get("FORCE_HTTPS"):
            return None
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        is_secure = request.is_secure or forwarded_proto.lower() == "https"
        if is_secure:
            return None
        secure_url = request.url.replace("http://", "https://", 1)
        return redirect(secure_url, code=308)

    @app.before_request
    def assign_request_id():
        """Attach a unique request ID for tracing and response correlation."""
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def attach_request_id(response):
        """Attach request/security headers and disable caching on sensitive routes."""
        response.headers["X-Request-ID"] = g.get("request_id", "")
        if app.config.get("SECURITY_HEADERS_ENABLED", True):
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault(
                "Permissions-Policy",
                app.config.get("PERMISSIONS_POLICY", "camera=(self), microphone=(), geolocation=()"),
            )
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
            response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
            response.headers.setdefault("X-DNS-Prefetch-Control", "off")
            response.headers.setdefault("Origin-Agent-Cluster", "?1")
            response.headers.setdefault(
                "Content-Security-Policy",
                _ensure_blob_img_src(app.config.get("CSP_POLICY", "default-src 'self'")),
            )
            if app.config.get("ENABLE_HSTS", True):
                max_age = int(app.config.get("HSTS_MAX_AGE", 31536000))
                response.headers.setdefault("Strict-Transport-Security", f"max-age={max_age}; includeSubDomains")

        is_authenticated_api = request.path.startswith("/api/") and bool(getattr(g, "user", None))
        is_authenticated_page = request.path in {"/predict", "/prices", "/profile", "/history"} and bool(
            session.get("user")
        )
        is_auth_page = request.path == "/auth"
        if (
            request.path.startswith("/api/auth")
            or request.path.startswith("/api/chat")
            or is_authenticated_api
            or is_authenticated_page
            or is_auth_page
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db(
            app.config["DATABASE_PATH"],
            app.config["SCHEMA_PATH"],
            force=bool(app.config.get("TESTING")),
        )
        db = get_db()
        seed_admin(db, app.config["ADMIN_USERNAME"], app.config["ADMIN_PASSWORD"])
        seed_vegetables(db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(veggie_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(views_bp)

    @app.get("/api/health")
    def health():
        """Return backend health status and discovered model names."""
        models = load_models_config(app.config["MODELS_ROOT"])
        return ok_response(
            {
                "status": "ok",
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "models": [model["name"] for model in models],
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")))
