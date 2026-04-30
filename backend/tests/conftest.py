"""Shared pytest fixtures for backend API, security, and E2E tests."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

import pytest
from PIL import Image

from backend.app import create_app
from backend.db import init_db
from backend.repository import seed_vegetables
from backend.utils.security import seed_admin


@pytest.fixture()
def app(tmp_path: Path):
    """Create a Flask test application backed by isolated SQLite storage."""
    database_path = tmp_path / "test.db"
    upload_directory = tmp_path / "uploads"
    upload_directory.mkdir(parents=True, exist_ok=True)

    config = {
        "TESTING": True,
        "DATABASE_PATH": str(database_path),
        "UPLOAD_DIR": str(upload_directory),
        "JWT_SECRET": "test-jwt",
        "SECRET_KEY": "test-secret",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "admin123",
        "MODEL_SERVICE_URL": "http://model-service",
        "SCHEMA_PATH": str(Path(__file__).resolve().parents[2] / "db" / "schema.sql"),
        "MODELS_ROOT": str(Path(__file__).resolve().parents[2] / "models"),
        "VEGNET_REMOTE_ENABLED": True,
        "VEGNET_23_URL": "https://example.com/v1/models/vegnet-23",
        "VEGNET_101_URL": "https://example.com/v1/models/vegnet-101",
        "VEGNET_REMOTE_TIMEOUT_SEC": 5,
        "VEGNET_REMOTE_RETRIES": 0,
        "VEGNET_23_RESAMPLE": "nearest",
        "VEGNET_101_RESAMPLE": "bicubic",
        "OPENAI_API_KEY": "",
        "CAPTCHA_ENABLED": False,
        "CAPTCHA_DEV_MODE": True,
        "OTP_ENABLED": False,
        "OTP_DEV_MODE": True,
    }
    flask_app = create_app(config)

    with flask_app.app_context():
        init_db(config["DATABASE_PATH"], config["SCHEMA_PATH"], force=True)
        from backend.db import get_db

        db = get_db()
        seed_admin(db, config["ADMIN_USERNAME"], config["ADMIN_PASSWORD"])
        seed_vegetables(db)

    yield flask_app


@pytest.fixture()
def client(app):
    """Return a Flask test client bound to the test application."""
    return app.test_client()


def make_image_bytes(color: tuple[int, int, int] = (120, 20, 200)) -> bytes:
    """Generate a small in-memory PNG image for upload tests."""
    image = Image.new("RGB", (32, 32), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture()
def auth_token(client) -> str:
    """Log in as admin and return a bearer token."""
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return response.get_json()["data"]["token"]


@pytest.fixture()
def auth_headers(auth_token: str) -> dict[str, str]:
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def bearer_headers() -> Callable[[str], dict[str, str]]:
    """Create authorization headers from an arbitrary token."""

    def _headers(token: str) -> dict[str, str]:
        """Build Bearer auth header dict."""
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture()
def signup_and_login(client) -> Callable[[str, str, str], str]:
    """Create a user and return a JWT token from login."""

    def _create(email: str, password: str = "pass1234", name: str = "Test User") -> str:
        """Sign up and log in a user for test setup."""
        client.application.config["CAPTCHA_ENABLED"] = False
        client.application.config["OTP_ENABLED"] = False

        signup = client.post(
            "/api/auth/signup",
            json={"name": name, "email": email, "password": password, "agree_terms": True},
        )
        assert signup.status_code == 201

        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        return login.get_json()["data"]["token"]

    return _create


@pytest.fixture()
def solve_captcha() -> Callable[[dict], str]:
    """Return a helper that resolves captcha answers in development mode."""

    def _solve(captcha_payload: dict) -> str:
        """Extract captcha plaintext from development-mode API payload."""
        answer = str(captcha_payload.get("captcha_text") or "").strip()
        if not answer:
            raise AssertionError("captcha_text is unavailable; enable CAPTCHA_DEV_MODE for test runs")
        return answer

    return _solve


@pytest.fixture(autouse=True)
def mock_veggie_remote_inference(request, monkeypatch):
    """Mock VegNet inference unless test explicitly requests the real inference code path."""
    if request.node.get_closest_marker("real_vegnet"):
        return

    def _mock_predict(model_name: str, endpoint: str, image_bytes: bytes, input_size: int) -> tuple[str, float]:
        """Return deterministic prediction labels for fast and stable tests."""
        del endpoint, image_bytes, input_size
        if model_name == "vegnet-101":
            return "Tomato", 96.7
        return "Potato", 94.2

    monkeypatch.setattr("backend.veggie._predict_remote_vegetable", _mock_predict)
