"""Configuration loading for the Flask backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get_env(name: str, default: str) -> str:
    """Return an environment variable value with a default."""
    return os.getenv(name, default)


def _get_int(name: str, default: int) -> int:
    """Return an integer environment variable or a default value."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_list(name: str, default: list[str]) -> list[str]:
    """Return a comma-separated environment variable as a list."""
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_bool(name: str, default: bool) -> bool:
    """Return a boolean environment variable or a default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    """Return a float environment variable or a default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _resolve_path(raw_value: str, repo_root: Path) -> str:
    """Resolve configured filesystem paths relative to repository root."""
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return str(candidate.resolve())


@dataclass
class Settings:
    """Typed runtime settings used by the backend service."""

    SECRET_KEY: str
    JWT_SECRET: str
    JWT_EXPIRES_MINUTES: int
    DATABASE_PATH: str
    MODEL_SERVICE_URL: str
    MODEL_SERVICE_TIMEOUT_SEC: int
    UPLOAD_DIR: str
    MAX_CONTENT_LENGTH: int
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    RATE_LIMIT_MAX: int
    RATE_LIMIT_WINDOW_SEC: int
    SCHEMA_PATH: str
    MODELS_ROOT: str
    CORS_ORIGINS: list[str]
    LOG_LEVEL: str
    OPENAI_API_KEY: str
    OPENAI_CHAT_MODEL: str
    OPENAI_TIMEOUT_SEC: int
    VEGGIE_DEFAULT_MODEL: str
    VEGNET_23_URL: str
    VEGNET_101_URL: str
    VEGNET_23_RESAMPLE: str
    VEGNET_101_RESAMPLE: str
    VEGNET_REMOTE_ENABLED: bool
    VEGNET_REMOTE_TIMEOUT_SEC: int
    VEGNET_REMOTE_RETRIES: int
    ROBOFLOW_API_KEY: str
    ROBOFLOW_MODEL_ID: str
    ROBOFLOW_BASE_URL: str
    ROBOFLOW_WORKSPACE: str
    ROBOFLOW_WORKFLOW_ID: str
    ROBOFLOW_WORKFLOW_IMAGE_INPUT: str
    ROBOFLOW_TIMEOUT_SEC: int
    ROBOFLOW_CONFIDENCE_THRESHOLD: float
    CAPTCHA_ENABLED: bool
    CAPTCHA_TTL_SEC: int
    CAPTCHA_LENGTH: int
    CAPTCHA_IMAGE_WIDTH: int
    CAPTCHA_IMAGE_HEIGHT: int
    CAPTCHA_DEV_MODE: bool
    OTP_ENABLED: bool
    OTP_LENGTH: int
    OTP_TTL_SEC: int
    OTP_MAX_ATTEMPTS: int
    OTP_DEV_MODE: bool
    PASSWORD_RESET_TTL_SEC: int
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    SMTP_USE_TLS: bool
    SMTP_USE_SSL: bool
    SECURITY_HEADERS_ENABLED: bool
    ENABLE_HSTS: bool
    HSTS_MAX_AGE: int
    FORCE_HTTPS: bool
    SESSION_COOKIE_SECURE: bool
    SESSION_COOKIE_HTTPONLY: bool
    SESSION_COOKIE_SAMESITE: str
    PERMISSIONS_POLICY: str
    CSP_POLICY: str

    def to_dict(self) -> dict:
        """Return settings as a plain dictionary for Flask config loading."""
        return self.__dict__


def load_settings() -> Settings:
    """Load backend settings from environment variables."""
    repo_root = Path(__file__).resolve().parents[1]
    default_schema = repo_root / "db" / "schema.sql"
    default_models_root = repo_root / "models"
    default_db = repo_root / "db" / "app.db"
    default_uploads = repo_root / "backend" / "uploads"
    database_path = _resolve_path(_get_env("DATABASE_PATH", str(default_db)), repo_root)
    schema_path = _resolve_path(_get_env("SCHEMA_PATH", str(default_schema)), repo_root)
    models_root = _resolve_path(_get_env("MODELS_ROOT", str(default_models_root)), repo_root)
    upload_dir = _resolve_path(_get_env("UPLOAD_DIR", str(default_uploads)), repo_root)
    return Settings(
        SECRET_KEY=_get_env("SECRET_KEY", "dev-session-secret-change-before-production"),
        JWT_SECRET=_get_env("JWT_SECRET", "dev-jwt-secret-change-before-production"),
        JWT_EXPIRES_MINUTES=_get_int("JWT_EXPIRES_MINUTES", 120),
        DATABASE_PATH=database_path,
        MODEL_SERVICE_URL=_get_env("MODEL_SERVICE_URL", "http://127.0.0.1:8000"),
        MODEL_SERVICE_TIMEOUT_SEC=_get_int("MODEL_SERVICE_TIMEOUT_SEC", 30),
        UPLOAD_DIR=upload_dir,
        MAX_CONTENT_LENGTH=_get_int("MAX_CONTENT_LENGTH", 8 * 1024 * 1024),
        ADMIN_USERNAME=_get_env("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD=_get_env("ADMIN_PASSWORD", "admin123"),
        RATE_LIMIT_MAX=_get_int("RATE_LIMIT_MAX", 5),
        RATE_LIMIT_WINDOW_SEC=_get_int("RATE_LIMIT_WINDOW_SEC", 300),
        SCHEMA_PATH=schema_path,
        MODELS_ROOT=models_root,
        CORS_ORIGINS=_get_list(
            "CORS_ORIGINS",
            [
                "http://localhost:5000",
                "http://127.0.0.1:5000",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
        ),
        LOG_LEVEL=_get_env("LOG_LEVEL", "INFO"),
        OPENAI_API_KEY=_get_env("OPENAI_API_KEY", ""),
        OPENAI_CHAT_MODEL=_get_env("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        OPENAI_TIMEOUT_SEC=_get_int("OPENAI_TIMEOUT_SEC", 20),
        VEGGIE_DEFAULT_MODEL=_get_env("VEGGIE_DEFAULT_MODEL", "vegnet-23"),
        VEGNET_23_URL=_get_env(
            "VEGNET_23_URL",
            "https://ca2-daaa2b02-p2415691-gohkunming.onrender.com/v1/models/vegnet-23",
        ),
        VEGNET_101_URL=_get_env(
            "VEGNET_101_URL",
            "https://ca2-daaa2b02-p2415691-gohkunming.onrender.com/v1/models/vegnet-101",
        ),
        VEGNET_23_RESAMPLE=_get_env("VEGNET_23_RESAMPLE", "nearest"),
        VEGNET_101_RESAMPLE=_get_env("VEGNET_101_RESAMPLE", "bicubic"),
        VEGNET_REMOTE_ENABLED=_get_bool("VEGNET_REMOTE_ENABLED", True),
        VEGNET_REMOTE_TIMEOUT_SEC=_get_int("VEGNET_REMOTE_TIMEOUT_SEC", 45),
        VEGNET_REMOTE_RETRIES=_get_int("VEGNET_REMOTE_RETRIES", 4),
        ROBOFLOW_API_KEY=_get_env("ROBOFLOW_API_KEY", ""),
        ROBOFLOW_MODEL_ID=_get_env("ROBOFLOW_MODEL_ID", ""),
        ROBOFLOW_BASE_URL=_get_env("ROBOFLOW_BASE_URL", "https://detect.roboflow.com"),
        ROBOFLOW_WORKSPACE=_get_env("ROBOFLOW_WORKSPACE", ""),
        ROBOFLOW_WORKFLOW_ID=_get_env("ROBOFLOW_WORKFLOW_ID", ""),
        ROBOFLOW_WORKFLOW_IMAGE_INPUT=_get_env("ROBOFLOW_WORKFLOW_IMAGE_INPUT", "image"),
        ROBOFLOW_TIMEOUT_SEC=_get_int("ROBOFLOW_TIMEOUT_SEC", 10),
        ROBOFLOW_CONFIDENCE_THRESHOLD=_get_float("ROBOFLOW_CONFIDENCE_THRESHOLD", 0.35),
        CAPTCHA_ENABLED=_get_bool("CAPTCHA_ENABLED", True),
        CAPTCHA_TTL_SEC=_get_int("CAPTCHA_TTL_SEC", 300),
        CAPTCHA_LENGTH=_get_int("CAPTCHA_LENGTH", 5),
        CAPTCHA_IMAGE_WIDTH=_get_int("CAPTCHA_IMAGE_WIDTH", 540),
        CAPTCHA_IMAGE_HEIGHT=_get_int("CAPTCHA_IMAGE_HEIGHT", 180),
        CAPTCHA_DEV_MODE=_get_bool("CAPTCHA_DEV_MODE", False),
        OTP_ENABLED=_get_bool("OTP_ENABLED", True),
        OTP_LENGTH=_get_int("OTP_LENGTH", 6),
        OTP_TTL_SEC=_get_int("OTP_TTL_SEC", 300),
        OTP_MAX_ATTEMPTS=_get_int("OTP_MAX_ATTEMPTS", 5),
        OTP_DEV_MODE=_get_bool("OTP_DEV_MODE", True),
        PASSWORD_RESET_TTL_SEC=_get_int("PASSWORD_RESET_TTL_SEC", 1800),
        SMTP_HOST=_get_env("SMTP_HOST", ""),
        SMTP_PORT=_get_int("SMTP_PORT", 587),
        SMTP_USERNAME=_get_env("SMTP_USERNAME", ""),
        SMTP_PASSWORD=_get_env("SMTP_PASSWORD", ""),
        SMTP_FROM_EMAIL=_get_env("SMTP_FROM_EMAIL", ""),
        SMTP_FROM_NAME=_get_env("SMTP_FROM_NAME", "VeggieAI Security"),
        SMTP_USE_TLS=_get_bool("SMTP_USE_TLS", True),
        SMTP_USE_SSL=_get_bool("SMTP_USE_SSL", False),
        SECURITY_HEADERS_ENABLED=_get_bool("SECURITY_HEADERS_ENABLED", True),
        ENABLE_HSTS=_get_bool("ENABLE_HSTS", True),
        HSTS_MAX_AGE=_get_int("HSTS_MAX_AGE", 31536000),
        FORCE_HTTPS=_get_bool("FORCE_HTTPS", False),
        SESSION_COOKIE_SECURE=_get_bool("SESSION_COOKIE_SECURE", False),
        SESSION_COOKIE_HTTPONLY=_get_bool("SESSION_COOKIE_HTTPONLY", True),
        SESSION_COOKIE_SAMESITE=_get_env("SESSION_COOKIE_SAMESITE", "Lax"),
        PERMISSIONS_POLICY=_get_env("PERMISSIONS_POLICY", "camera=(self), microphone=(), geolocation=()"),
        CSP_POLICY=_get_env(
            "CSP_POLICY",
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
            "object-src 'none'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https:; connect-src 'self' https: http:",
        ),
    )
