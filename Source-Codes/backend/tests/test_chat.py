"""Chat API tests for per-user conversation history and OpenAI integration."""

from __future__ import annotations

import io
import json

import pytest
import responses

from .conftest import make_image_bytes

pytestmark = [pytest.mark.api]


def _login(client):
    """Authenticate admin and return a JWT."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.get_json()["data"]["token"]


def _signup_and_login(client, email: str):
    """Create and authenticate a non-admin user."""
    signup = client.post(
        "/api/auth/signup",
        json={"name": "Chat User", "email": email, "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201
    login = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    assert login.status_code == 200
    return login.get_json()["data"]["token"]


def _mock_openai_reply(text: str):
    """Register a deterministic mock response for OpenAI chat completion."""
    responses.add(
        responses.POST,
        "https://api.openai.com/v1/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": text,
                    }
                }
            ]
        },
        status=200,
    )


@pytest.mark.expected_failure
def test_chat_requires_auth(client):
    """Reject unauthenticated access to chat endpoints."""
    assert client.get("/api/chat/history").status_code == 401
    assert client.post("/api/chat/message", json={"message": "hello"}).status_code == 401
    assert client.delete("/api/chat/history").status_code == 401
    assert client.get("/api/chat/conversations").status_code == 401
    assert client.post("/api/chat/conversations", json={}).status_code == 401


@responses.activate
def test_chat_message_and_history(client):
    """Store user and assistant messages and return ordered history."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    _mock_openai_reply("Tomato is a fruit vegetable rich in lycopene.")

    token = _login(client)
    send = client.post(
        "/api/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Tell me about tomato nutrition"},
    )
    assert send.status_code == 200
    assert send.get_json()["data"]["message"]["role"] == "assistant"

    history = client.get("/api/chat/history", headers={"Authorization": f"Bearer {token}"})
    assert history.status_code == 200
    messages = history.get_json()["data"]["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_chat_rejects_non_vegetable_topics_with_guardrail(client):
    """Return a scoped guardrail answer for out-of-domain questions."""
    token = _login(client)
    response = client.post(
        "/api/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Write me a Python quicksort implementation."},
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["guardrail"]["scope_restricted"] is True
    assert "I can only help with vegetable-related topics" in payload["message"]["content"]


@responses.activate
def test_chat_rag_includes_price_context(client):
    """Inject price context that matches the `/api/veggie/prices` response values."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    captured_payload: dict[str, object] = {}

    def _callback(request):
        """Capture OpenAI payload and return a mock assistant response."""
        body = request.body.decode("utf-8") if isinstance(request.body, (bytes, bytearray)) else request.body
        captured_payload.update(json.loads(body))
        body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Tomato prices differ by retailer.",
                    }
                }
            ]
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(body))

    responses.add_callback(
        responses.POST,
        "https://api.openai.com/v1/chat/completions",
        callback=_callback,
        content_type="application/json",
    )

    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    prices_response = client.get("/api/veggie/prices", headers=headers)
    assert prices_response.status_code == 200
    vegetables = prices_response.get_json()["data"]["vegetables"]
    tomato = next(item for item in vegetables if item.get("key") == "tomato")
    expected_tomato_line = (
        f"Tomato: NTUC S${float(tomato['prices']['ntuc']):.2f}, "
        f"Giant S${float(tomato['prices']['giant']):.2f}, "
        f"Cold Storage S${float(tomato['prices']['coldStorage']):.2f}, "
        f"Sheng Siong S${float(tomato['prices']['shengSiong']):.2f} per {tomato.get('unit', 'unit')}"
    )

    send = client.post(
        "/api/chat/message",
        headers=headers,
        json={"message": "What is the tomato price at NTUC and Giant?"},
    )
    assert send.status_code == 200
    messages = captured_payload["messages"]
    assert isinstance(messages, list)
    merged = "\n".join(str(item.get("content") or "") for item in messages if isinstance(item, dict))
    assert "Retrieved Knowledge:" in merged
    assert "Current Prices (SGD):" in merged
    assert expected_tomato_line in merged
    assert "NTUC" in merged
    assert "Giant" in merged


@responses.activate
def test_chat_rag_includes_recent_memory(client):
    """Include prior turns in later OpenAI payloads for conversation memory."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    captured_payloads: list[dict] = []

    def _callback(request):
        """Capture each OpenAI payload and return turn-aware replies."""
        body = request.body.decode("utf-8") if isinstance(request.body, (bytes, bytearray)) else request.body
        payload = json.loads(body)
        captured_payloads.append(payload)
        turn_index = len(captured_payloads)
        body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"Turn {turn_index} reply",
                    }
                }
            ]
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(body))

    responses.add_callback(
        responses.POST,
        "https://api.openai.com/v1/chat/completions",
        callback=_callback,
        content_type="application/json",
    )

    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/api/chat/message", headers=headers, json={"message": "Tell me about tomato nutrition"})
    assert first.status_code == 200
    second = client.post("/api/chat/message", headers=headers, json={"message": "What about its price at NTUC?"})
    assert second.status_code == 200

    assert len(captured_payloads) == 2
    second_messages = captured_payloads[1]["messages"]
    merged_second = "\n".join(str(item.get("content") or "") for item in second_messages if isinstance(item, dict))
    assert "Tell me about tomato nutrition" in merged_second
    assert "Turn 1 reply" in merged_second


@responses.activate
def test_chat_rag_includes_location_guidance_when_user_shares_location(client):
    """Include location context and map links when user states where they stay."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    captured_payload: dict[str, object] = {}

    def _callback(request):
        """Capture OpenAI payload and return deterministic assistant text."""
        body = request.body.decode("utf-8") if isinstance(request.body, (bytes, bytearray)) else request.body
        captured_payload.update(json.loads(body))
        response_body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Check nearby stores in Tampines using the provided links.",
                    }
                }
            ]
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))

    responses.add_callback(
        responses.POST,
        "https://api.openai.com/v1/chat/completions",
        callback=_callback,
        content_type="application/json",
    )

    token = _login(client)
    response = client.post(
        "/api/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "I stay in Tampines. Where can I buy tomato at good price?"},
    )
    assert response.status_code == 200

    messages = captured_payload["messages"]
    assert isinstance(messages, list)
    merged = "\n".join(str(item.get("content") or "") for item in messages if isinstance(item, dict))
    assert "User Location Context:" in merged
    assert "User-stated location: Tampines" in merged
    assert "Store locator links:" in merged
    assert "google.com/maps/search" in merged
    assert "Price Intelligence:" in merged


@responses.activate
def test_location_only_followup_is_allowed_after_vegetable_context(client):
    """Treat location-only message as in-scope follow-up after veggie discussion."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    _mock_openai_reply("Tomato is rich in lycopene.")
    _mock_openai_reply("Thanks, I will use your location to suggest nearby stores.")

    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/api/chat/message", headers=headers, json={"message": "Tell me about tomato nutrition"})
    assert first.status_code == 200

    second = client.post("/api/chat/message", headers=headers, json={"message": "I stay in Tampines."})
    assert second.status_code == 200
    payload = second.get_json()["data"]
    assert payload["message"]["role"] == "assistant"
    assert "guardrail" not in payload


@responses.activate
@pytest.mark.consistency
def test_chat_rag_includes_prediction_memory_lines(client):
    """Include recent prediction memory in the retrieved OpenAI context."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    captured_payload: dict[str, object] = {}

    def _callback(request):
        """Capture OpenAI payload and return deterministic assistant text."""
        body = request.body.decode("utf-8") if isinstance(request.body, (bytes, bytearray)) else request.body
        captured_payload.update(json.loads(body))
        response_body = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "You previously classified tomato using VegNet-101.",
                    }
                }
            ]
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))

    responses.add_callback(
        responses.POST,
        "https://api.openai.com/v1/chat/completions",
        callback=_callback,
        content_type="application/json",
    )

    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    image_bytes = make_image_bytes()
    prediction = client.post(
        "/api/veggie/predict",
        headers=headers,
        data={"image": (io.BytesIO(image_bytes), "memory.png"), "model_name": "vegnet-101"},
        content_type="multipart/form-data",
    )
    assert prediction.status_code == 201

    send = client.post(
        "/api/chat/message",
        headers=headers,
        json={"message": "What vegetable did I classify before?"},
    )
    assert send.status_code == 200

    messages = captured_payload["messages"]
    assert isinstance(messages, list)
    merged = "\n".join(str(item.get("content") or "") for item in messages if isinstance(item, dict))
    assert "User Prediction Memory:" in merged
    assert "using vegnet-101" in merged


@pytest.mark.unit
@pytest.mark.validity
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("I stay in Tampines. Where can I buy tomato?", "tampines"),
        ("My location is yishun and I need cabbage", "yishun"),
        ("I am from Jurong East and need broccoli", "jurong east"),
    ],
)
def test_location_extraction_patterns_cover_common_user_phrases(message: str, expected: str):
    """Extract normalized location strings used by RAG location guidance."""
    from backend.chat import _extract_location_from_text

    location = _extract_location_from_text(message)
    assert location == expected


@responses.activate
@pytest.mark.consistency
def test_chat_history_is_scoped_per_user(client):
    """Keep chat history isolated per authenticated user."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    _mock_openai_reply("Admin reply")
    _mock_openai_reply("User reply")

    admin_token = _login(client)
    user_token = _signup_and_login(client, "chat-user@example.com")

    admin_send = client.post(
        "/api/chat/message",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"message": "Admin tomato question"},
    )
    assert admin_send.status_code == 200

    user_send = client.post(
        "/api/chat/message",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"message": "User potato question"},
    )
    assert user_send.status_code == 200

    admin_history = client.get("/api/chat/history", headers={"Authorization": f"Bearer {admin_token}"})
    user_history = client.get("/api/chat/history", headers={"Authorization": f"Bearer {user_token}"})

    assert admin_history.status_code == 200
    assert user_history.status_code == 200

    admin_messages = admin_history.get_json()["data"]["messages"]
    user_messages = user_history.get_json()["data"]["messages"]

    assert len(admin_messages) == 2
    assert len(user_messages) == 2
    assert admin_messages[0]["content"] == "Admin tomato question"
    assert user_messages[0]["content"] == "User potato question"


@responses.activate
def test_chat_clear_history(client):
    """Allow authenticated users to clear their own chat history."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    _mock_openai_reply("Clearable reply")
    token = _login(client)

    send = client.post(
        "/api/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Keep this tomato price context"},
    )
    assert send.status_code == 200

    clear = client.delete("/api/chat/history", headers={"Authorization": f"Bearer {token}"})
    assert clear.status_code == 200
    assert clear.get_json()["data"]["deleted"] >= 1

    history = client.get("/api/chat/history", headers={"Authorization": f"Bearer {token}"})
    assert history.status_code == 200
    assert history.get_json()["data"]["messages"] == []


@responses.activate
@pytest.mark.consistency
def test_chat_supports_multiple_conversations_per_user(client):
    """Allow users to create/switch isolated chat threads."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    _mock_openai_reply("First thread answer")
    _mock_openai_reply("Second thread answer")
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    first_send = client.post(
        "/api/chat/message",
        headers=headers,
        json={"message": "Tell me about carrots"},
    )
    assert first_send.status_code == 200
    first_conversation = int(first_send.get_json()["data"]["conversation_id"])

    create_second = client.post("/api/chat/conversations", headers=headers, json={"title": "Price planning"})
    assert create_second.status_code == 201
    second_conversation = int(create_second.get_json()["data"]["conversation"]["id"])
    assert second_conversation != first_conversation

    second_send = client.post(
        "/api/chat/message",
        headers=headers,
        json={"message": "Compare tomato prices", "conversation_id": second_conversation},
    )
    assert second_send.status_code == 200
    assert int(second_send.get_json()["data"]["conversation_id"]) == second_conversation

    first_history = client.get(
        f"/api/chat/history?conversation_id={first_conversation}",
        headers=headers,
    )
    second_history = client.get(
        f"/api/chat/history?conversation_id={second_conversation}",
        headers=headers,
    )
    assert first_history.status_code == 200
    assert second_history.status_code == 200

    first_messages = first_history.get_json()["data"]["messages"]
    second_messages = second_history.get_json()["data"]["messages"]
    assert len(first_messages) == 2
    assert len(second_messages) == 2
    assert first_messages[0]["content"] == "Tell me about carrots"
    assert second_messages[0]["content"] == "Compare tomato prices"

    conversation_list = client.get("/api/chat/conversations", headers=headers)
    assert conversation_list.status_code == 200
    conversations = conversation_list.get_json()["data"]["conversations"]
    ids = {int(item["id"]) for item in conversations}
    assert first_conversation in ids
    assert second_conversation in ids


@responses.activate
@pytest.mark.security
def test_chat_rejects_cross_user_conversation_access(client):
    """Reject cross-user conversation IDs for message and history endpoints."""
    client.application.config["OPENAI_API_KEY"] = "test-openai-key"
    _mock_openai_reply("Owner reply")

    owner_token = _login(client)
    other_token = _signup_and_login(client, "chat-other@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    owner_send = client.post(
        "/api/chat/message",
        headers=owner_headers,
        json={"message": "Tomato facts"},
    )
    assert owner_send.status_code == 200
    owner_conversation = int(owner_send.get_json()["data"]["conversation_id"])

    other_history = client.get(
        f"/api/chat/history?conversation_id={owner_conversation}",
        headers=other_headers,
    )
    assert other_history.status_code == 404

    other_send = client.post(
        "/api/chat/message",
        headers=other_headers,
        json={"message": "Steal context", "conversation_id": owner_conversation},
    )
    assert other_send.status_code == 404
