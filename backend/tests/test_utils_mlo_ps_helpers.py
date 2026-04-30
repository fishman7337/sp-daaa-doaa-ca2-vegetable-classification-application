"""Focused coverage for backend utility helpers used by CI/MLOps gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.utils import mailer
from backend.utils.models_config import load_models_config, model_names
from backend.utils.search import build_where_clause, parse_search_query
from backend.veggie_catalog import (
    build_price_details,
    confidence_from_hash,
    normalize_vegetable_key,
    pick_vegetable_from_hash,
    serialize_catalog_item,
)

pytestmark = [pytest.mark.unit]


class _FakeSMTP:
    """Small SMTP test double that records sent messages."""

    instances: list["_FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged_in: tuple[str, str] | None = None
        self.messages = []
        self.tls_started = False
        self.ehlo_count = 0
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def ehlo(self) -> None:
        self.ehlo_count += 1

    def starttls(self) -> None:
        self.tls_started = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def send_message(self, message) -> None:
        self.messages.append(message)


def test_mailer_reports_missing_smtp_config(app):
    """Return a deterministic error when SMTP settings are incomplete."""
    with app.app_context():
        assert mailer.send_otp_email("user@example.com", "123456") == (False, "SMTP is not configured")
        assert mailer.send_password_reset_email("user@example.com", "https://example.test/reset", 60) == (
            False,
            "SMTP is not configured",
        )


def test_mailer_sends_otp_with_tls_and_login(app, monkeypatch):
    """Build and send an OTP email through STARTTLS when configured."""
    _FakeSMTP.instances = []
    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeSMTP)
    app.config.update(
        SMTP_HOST="smtp.example.test",
        SMTP_PORT=587,
        SMTP_USERNAME="mailer",
        SMTP_PASSWORD="secret",
        SMTP_FROM_EMAIL="security@example.test",
        SMTP_FROM_NAME="VeggieAI Security",
        SMTP_USE_TLS=True,
        SMTP_USE_SSL=False,
    )

    with app.app_context():
        ok, error = mailer.send_otp_email("user@example.com", "654321")

    assert ok is True
    assert error is None
    smtp = _FakeSMTP.instances[-1]
    assert smtp.tls_started is True
    assert smtp.logged_in == ("mailer", "secret")
    assert smtp.messages[-1]["Subject"] == "Your VeggieAI OTP Code"
    assert "654321" in smtp.messages[-1].get_content()


def test_mailer_sends_password_reset_with_ssl(app, monkeypatch):
    """Build and send a password reset email through SMTP over SSL."""
    _FakeSMTP.instances = []
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _FakeSMTP)
    app.config.update(
        SMTP_HOST="smtp.example.test",
        SMTP_PORT=465,
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="security@example.test",
        SMTP_FROM_NAME="VeggieAI Security",
        SMTP_USE_TLS=False,
        SMTP_USE_SSL=True,
    )

    with app.app_context():
        ok, error = mailer.send_password_reset_email("user@example.com", "https://example.test/reset", 120)

    assert ok is True
    assert error is None
    message = _FakeSMTP.instances[-1].messages[-1]
    assert message["Subject"] == "Reset your VeggieAI password"
    assert "https://example.test/reset" in message.get_content()
    assert "2 minutes" in message.get_content()


def test_mailer_sends_otp_with_ssl_and_reset_without_tls(app, monkeypatch):
    """Cover the alternate SSL OTP and plain SMTP reset branches."""
    _FakeSMTP.instances = []
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _FakeSMTP)
    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeSMTP)
    app.config.update(
        SMTP_HOST="smtp.example.test",
        SMTP_PORT=465,
        SMTP_USERNAME="mailer",
        SMTP_PASSWORD="secret",
        SMTP_FROM_EMAIL="security@example.test",
        SMTP_FROM_NAME="VeggieAI Security",
        SMTP_USE_TLS=False,
        SMTP_USE_SSL=True,
    )

    with app.app_context():
        ok, error = mailer.send_otp_email("user@example.com", "111222")

    assert ok is True
    assert error is None
    assert _FakeSMTP.instances[-1].logged_in == ("mailer", "secret")
    assert "111222" in _FakeSMTP.instances[-1].messages[-1].get_content()

    app.config.update(SMTP_PORT=587, SMTP_USE_SSL=False)
    with app.app_context():
        ok, error = mailer.send_password_reset_email("user@example.com", "https://example.test/plain", 30)

    assert ok is True
    assert error is None
    plain_smtp = _FakeSMTP.instances[-1]
    assert plain_smtp.tls_started is False
    assert plain_smtp.logged_in == ("mailer", "secret")
    assert "1 minutes" in plain_smtp.messages[-1].get_content()


def test_search_query_parser_and_where_clause_cover_all_filters():
    """Parse token, operator, date, free-text, and explicit filter inputs."""
    parsed = parse_search_query(
        "label:Potato model:model_a user:admin date:2026-01-01 conf>=90 latency<250 crispy notes unknown:value"
    )
    assert ("label", ":", "Potato") in parsed.filters
    assert ("conf", ">=", "90") in parsed.filters
    assert parsed.free_text == ["crispy", "notes", "unknown:value"]

    where_sql, params = build_where_clause(
        "date:2026-01-01..2026-01-03 conf>88 latency<=300 free text invalid_date:bad",
        {
            "model": "model_a",
            "label": "Potato",
            "user": "admin",
            "date_from": "2026-01-01",
            "date_to": "2026-02-01",
            "conf_min": 70,
            "conf_max": 99,
            "latency_max": 500,
        },
    )

    assert where_sql.startswith(" WHERE ")
    assert "p.created_at >= ? AND p.created_at < ?" in where_sql
    assert "p.top1_conf > ?" in where_sql
    assert "p.latency_ms <= ?" in where_sql
    assert "(p.top1_label LIKE ? OR p.notes LIKE ? OR p.input_ref LIKE ?)" in where_sql
    assert params[:4] == ["2026-01-01", "2026-01-04", 88.0, 300.0]
    assert params[-3:] == [70, 99, 500]


def test_search_query_ignores_invalid_numeric_and_date_filters():
    """Ignore malformed advanced-search filters instead of raising."""
    where_sql, params = build_where_clause("date:not-a-date conf>bad latency<slow", {})
    assert where_sql == ""
    assert params == []


def test_models_config_loads_manifest_and_directory_fallback(tmp_path: Path):
    """Load model names from both manifest and directory fallback layouts."""
    models_root = tmp_path / "models"
    model_a = models_root / "model_a"
    model_b = models_root / "model_b"
    model_a.mkdir(parents=True)
    model_b.mkdir(parents=True)
    (model_a / "labels.json").write_text(json.dumps(["carrot"]), encoding="utf-8")
    (model_b / "labels.json").write_text(json.dumps(["tomato"]), encoding="utf-8")
    (models_root / "models.json").write_text(
        json.dumps(
            {
                "models": [
                    {"name": "model_a", "path": "model_a"},
                    {"name": "", "path": "ignored"},
                    {"name": "model_b", "path": "model_b", "labels": "missing.json"},
                ]
            }
        ),
        encoding="utf-8",
    )

    loaded = load_models_config(str(models_root))
    assert loaded == [{"name": "model_a", "labels": ["carrot"]}, {"name": "model_b", "labels": []}]
    assert model_names(str(models_root)) == {"model_a", "model_b"}

    (models_root / "models.json").unlink()
    fallback = load_models_config(str(models_root))
    assert {item["name"] for item in fallback} == {"model_a", "model_b"}


def test_veggie_catalog_helpers_are_deterministic_and_serializable():
    """Cover deterministic catalog helpers used by price and prediction APIs."""
    assert normalize_vegetable_key("") == ""
    assert normalize_vegetable_key("Bitter Gourd") == "bitter_gourd"
    assert normalize_vegetable_key("Cauliflower_and_Broccoli") == "cauliflower_and_broccoli"
    assert normalize_vegetable_key("unknown vegetable") == "unknown vegetable"

    digest = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    assert isinstance(pick_vegetable_from_hash(digest), str)
    assert 80.0 <= confidence_from_hash(digest) <= 99.9

    item = {
        "name": "Potato",
        "prices": {"ntuc": 2.2, "giant": 2.0, "coldStorage": 2.6, "shengSiong": 1.9},
    }
    serialized = serialize_catalog_item(item)
    assert serialized["prices"] == item["prices"]
    assert set(serialized["priceDetails"]) == {"ntuc", "giant", "coldStorage", "shengSiong"}

    details = build_price_details(item["prices"])
    for market in details.values():
        prices = [row["price"] for row in market["variations"]]
        assert prices == sorted(prices)
