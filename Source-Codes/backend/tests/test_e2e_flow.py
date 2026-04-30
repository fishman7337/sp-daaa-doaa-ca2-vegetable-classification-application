"""End-to-end tests that validate secure multi-step user journeys."""

from __future__ import annotations

import io

import pytest
import responses

from .conftest import make_image_bytes

pytestmark = [pytest.mark.e2e]


def _register_openai_mock(reply: str):
    """Register a mock OpenAI completion response."""
    responses.add(
        responses.POST,
        "https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "content": reply}}]},
        status=200,
    )


@responses.activate
def test_e2e_secure_auth_predict_and_chat_flow(client, solve_captcha):
    """Exercise signup, OTP, model predict, history, and chatbot in one flow."""
    client.application.config.update(
        {
            "CAPTCHA_ENABLED": True,
            "CAPTCHA_DEV_MODE": True,
            "OTP_ENABLED": True,
            "OTP_DEV_MODE": True,
            "OPENAI_API_KEY": "test-openai-key",
        }
    )

    captcha = client.get("/api/auth/captcha")
    assert captcha.status_code == 200
    captcha_payload = captcha.get_json()["data"]
    assert captcha_payload["enabled"] is True
    captcha_answer = solve_captcha(captcha_payload)

    signup = client.post(
        "/api/auth/signup",
        json={
            "name": "E2E User",
            "email": "e2e-user@example.com",
            "password": "pass1234",
            "agree_terms": True,
            "captcha_id": captcha_payload["captcha_id"],
            "captcha_answer": captcha_answer,
        },
    )
    assert signup.status_code == 201
    signup_payload = signup.get_json()["data"]
    assert signup_payload["otp_required"] is True
    assert signup_payload["otp_session"]
    assert signup_payload["dev_otp"]

    verify = client.post(
        "/api/auth/otp/verify",
        json={
            "otp_session": signup_payload["otp_session"],
            "otp_code": signup_payload["dev_otp"],
        },
    )
    assert verify.status_code == 200
    token = verify.get_json()["data"]["token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    models = client.get("/api/veggie/models", headers=auth_headers)
    assert models.status_code == 200
    models_payload = models.get_json()["data"]
    assert any(model["name"] == "vegnet-23" for model in models_payload["models"])
    assert any(model["name"] == "vegnet-101" for model in models_payload["models"])

    catalog = client.get("/api/veggie/catalog", headers=auth_headers)
    assert catalog.status_code == 200
    assert catalog.get_json()["data"]["vegetables"]

    prices = client.get("/api/veggie/prices", headers=auth_headers)
    assert prices.status_code == 200
    assert prices.get_json()["data"]["vegetables"]

    image_bytes = make_image_bytes()
    prediction = client.post(
        "/api/veggie/predict",
        data={"image": (io.BytesIO(image_bytes), "sample.png"), "model_name": "vegnet-101"},
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert prediction.status_code == 201
    prediction_payload = prediction.get_json()["data"]["prediction"]
    assert prediction_payload["modelName"] == "vegnet-101"

    history = client.get("/api/veggie/history", headers=auth_headers)
    assert history.status_code == 200
    items = history.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["modelName"] == "vegnet-101"

    _register_openai_mock("Use spinach and broccoli for a balanced iron and vitamin-rich meal.")
    chat = client.post(
        "/api/chat/message",
        headers=auth_headers,
        json={"message": "Give me nutrition advice"},
    )
    assert chat.status_code == 200
    assert chat.get_json()["data"]["message"]["role"] == "assistant"

    chat_history = client.get("/api/chat/history", headers=auth_headers)
    assert chat_history.status_code == 200
    messages = chat_history.get_json()["data"]["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
