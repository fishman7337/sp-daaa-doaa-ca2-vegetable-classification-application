"""Vegetable-scoped chatbot routes with retrieval-augmented generation."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus

import requests
from flask import Blueprint, current_app, g, request

from .db import get_db
from .repository import (
    clear_chat_messages,
    create_chat_conversation,
    ensure_chat_conversation,
    get_chat_conversation,
    insert_chat_message,
    list_chat_conversations,
    list_chat_messages,
    list_recent_chat_messages,
    list_vegetables,
    list_veggie_predictions,
    seed_vegetables,
)
from .utils.jwt import jwt_required
from .utils.responses import error_response, ok_response

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

OUT_OF_SCOPE_REPLY = (
    "I can only help with vegetable-related topics such as identification, nutrition, storage, and prices in this app."
)
SYSTEM_PROMPT = (
    "You are VeggieAI's assistant.\n"
    "Scope rules:\n"
    "1) Only answer questions about vegetables, vegetable prices, nutrition, storage, and user veggie predictions.\n"
    "2) If a question is outside this scope, respond exactly with: "
    '"I can only help with vegetable-related topics such as identification, nutrition, storage, and prices in this app."\n'
    "3) For price questions, rely on the retrieved context from the application and do not invent prices.\n"
    "4) If user location is provided in context, include nearby-store guidance using the provided store locator links.\n"
    "5) Keep answers concise and practical."
)
DOMAIN_KEYWORDS = {
    "vegetable",
    "veggie",
    "nutrition",
    "vitamin",
    "fiber",
    "fibre",
    "calorie",
    "healthy",
    "recipe",
    "cook",
    "storage",
    "shelf life",
    "freshness",
    "price",
    "prices",
    "cost",
    "ntuc",
    "giant",
    "cold storage",
    "sheng siong",
    "predict",
    "prediction",
    "model",
    "vegnet",
}
FOLLOW_UP_KEYWORDS = {
    "what about",
    "how about",
    "and",
    "also",
    "same",
    "that one",
    "it",
    "those",
    "them",
}
LOCATION_INTENT_KEYWORDS = {
    "near me",
    "nearby",
    "around me",
    "close to me",
    "where can i buy",
    "where should i buy",
    "i stay",
    "i live",
    "i am in",
    "i m in",
    "i am from",
    "i m from",
    "my location is",
}
LOCATION_PATTERNS = [
    re.compile(r"\b(?:i|we)\s+(?:live|stay|staying)\s+(?:in|at)\s+([a-z0-9][a-z0-9\s\-]{1,48})"),
    re.compile(r"\b(?:i|we)\s+(?:am|m|are)\s+(?:in|at|from)\s+([a-z0-9][a-z0-9\s\-]{1,48})"),
    re.compile(r"\bmy\s+location\s+is\s+([a-z0-9][a-z0-9\s\-]{1,48})"),
]
LOCATION_STOPWORDS = {
    "for",
    "to",
    "where",
    "which",
    "what",
    "and",
    "but",
    "because",
    "if",
    "so",
    "that",
    "about",
}
ZONE_KEYWORDS = {
    "east": {
        "tampines",
        "bedok",
        "pasir ris",
        "simei",
        "changi",
        "marine parade",
        "east coast",
    },
    "west": {
        "jurong",
        "clementi",
        "bukit batok",
        "bukit panjang",
        "choa chu kang",
        "boon lay",
    },
    "north": {
        "woodlands",
        "yishun",
        "sembawang",
        "marsiling",
        "admiralty",
    },
    "north-east": {
        "serangoon",
        "hougang",
        "sengkang",
        "punggol",
        "kovan",
    },
    "central": {
        "orchard",
        "novena",
        "bishan",
        "toa payoh",
        "queenstown",
        "bugis",
        "kallang",
        "newton",
        "city hall",
    },
}
PRICE_CHAINS = {
    "ntuc": "NTUC FairPrice",
    "giant": "Giant",
    "coldStorage": "Cold Storage",
    "shengSiong": "Sheng Siong",
}


def _parse_limit(raw: str | None, default: int, max_value: int) -> int:
    """Parse list-limit query parameter with min/max clamping."""
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return min(max(value, 1), max_value)


def _parse_optional_positive_int(raw: object, field_name: str) -> int | None:
    """Parse optional positive integer payload/query fields."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _normalize_text(value: str) -> str:
    """Normalize text for lightweight lexical matching."""
    lowered = value.strip().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", lowered)).strip()


def _vegetable_terms(item: dict) -> set[str]:
    """Build normalized lookup terms for one vegetable catalog item."""
    name = _normalize_text(str(item.get("name") or ""))
    key = _normalize_text(str(item.get("key") or ""))
    scientific = _normalize_text(str(item.get("scientificName") or ""))
    terms = {term for term in {name, key, scientific} if term}

    for raw_term in list(terms):
        if "_" in raw_term:
            terms.add(raw_term.replace("_", " "))
    return terms


def _message_has_domain_signal(message: str, catalog: list[dict]) -> bool:
    """Determine whether a message is within the vegetable chatbot scope."""
    normalized = _normalize_text(message)
    if not normalized:
        return False

    if any(keyword in normalized for keyword in DOMAIN_KEYWORDS):
        return True

    for item in catalog:
        if any(term and term in normalized for term in _vegetable_terms(item)):
            return True
    return False


def _is_vegetable_related(message: str, catalog: list[dict], history: list[dict]) -> bool:
    """Check relevance with follow-up awareness using recent conversation memory."""
    if _message_has_domain_signal(message, catalog):
        return True

    prior_turns = [item for item in history[:-1] if item.get("role") in {"user", "assistant"}]
    prior_has_domain = any(_message_has_domain_signal(str(item.get("content") or ""), catalog) for item in prior_turns)
    if _has_location_intent(message) and prior_has_domain:
        return True

    normalized = _normalize_text(message)
    is_follow_up = any(keyword in normalized for keyword in FOLLOW_UP_KEYWORDS)
    if not is_follow_up:
        return False

    return prior_has_domain


def _has_location_intent(message: str) -> bool:
    """Return whether a message requests location-aware recommendations."""
    normalized = _normalize_text(message)
    return any(keyword in normalized for keyword in LOCATION_INTENT_KEYWORDS)


def _trim_location_phrase(raw_location: str) -> str:
    """Trim trailing non-location words from an extracted location phrase."""
    tokens = [token for token in _normalize_text(raw_location).split() if token]
    cleaned: list[str] = []
    for token in tokens:
        if token in LOCATION_STOPWORDS:
            break
        cleaned.append(token)
    if not cleaned:
        return ""
    return " ".join(cleaned[:4])


def _extract_location_from_text(message: str) -> str | None:
    """Extract a candidate location phrase from one free-text user message."""
    normalized = _normalize_text(message)
    for pattern in LOCATION_PATTERNS:
        match = pattern.search(normalized)
        if not match:
            continue
        candidate = _trim_location_phrase(match.group(1))
        if len(candidate) < 2:
            continue
        return candidate
    return None


def _latest_user_location(history: list[dict]) -> str | None:
    """Find the most recent user-stated location from chat history."""
    for item in reversed(history):
        if item.get("role") != "user":
            continue
        location = _extract_location_from_text(str(item.get("content") or ""))
        if location:
            return location
    return None


def _infer_zone_from_location(location: str) -> str | None:
    """Infer a coarse Singapore zone from a user-provided location string."""
    normalized = _normalize_text(location)
    for zone, keywords in ZONE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return zone
    return None


def _select_relevant_catalog_items(user_message: str, catalog: list[dict], limit: int = 5) -> list[dict]:
    """Select the most relevant vegetables for retrieval context."""
    normalized = _normalize_text(user_message)
    scored_items: list[tuple[int, dict]] = []

    for item in catalog:
        score = 0
        terms = _vegetable_terms(item)
        for term in terms:
            if not term:
                continue
            if term == normalized:
                score += 8
            elif term in normalized:
                score += 5
            elif any(token == term for token in normalized.split()):
                score += 2
        if score > 0:
            scored_items.append((score, item))

    if scored_items:
        scored_items.sort(key=lambda entry: (-entry[0], str(entry[1].get("name") or "")))
        return [item for _, item in scored_items[:limit]]

    if "price" in normalized or "cost" in normalized or "list" in normalized:
        return catalog[:limit]
    return []


def _format_price_line(item: dict) -> str:
    """Format one vegetable price row for retrieval context."""
    prices = item.get("prices") or {}
    return (
        f"{item['name']}: NTUC S${float(prices.get('ntuc', 0.0)):.2f}, "
        f"Giant S${float(prices.get('giant', 0.0)):.2f}, "
        f"Cold Storage S${float(prices.get('coldStorage', 0.0)):.2f}, "
        f"Sheng Siong S${float(prices.get('shengSiong', 0.0)):.2f} per {item.get('unit', 'unit')}"
    )


def _summarize_cheapest_chains(items: list[dict]) -> str:
    """Summarize which retailer is cheapest across retrieved vegetables."""
    counts = {key: 0 for key in PRICE_CHAINS}
    considered = 0

    for item in items:
        prices = item.get("prices") or {}
        if not prices:
            continue
        available: dict[str, float] = {}
        for key in PRICE_CHAINS:
            value = prices.get(key)
            if value is None:
                continue
            try:
                available[key] = float(value)
            except (TypeError, ValueError):
                continue
        if not available:
            continue

        cheapest_key = min(available, key=available.get)
        counts[cheapest_key] += 1
        considered += 1

    if considered == 0:
        return "No comparable price entries were found."

    ranking = sorted(
        ((chain, count) for chain, count in counts.items() if count > 0),
        key=lambda entry: (-entry[1], PRICE_CHAINS[entry[0]]),
    )
    summary = ", ".join(f"{PRICE_CHAINS[chain]} ({count})" for chain, count in ranking)
    return f"Cheapest-chain wins across {considered} retrieved vegetables: {summary}."


def _build_store_locator_links(location: str) -> list[str]:
    """Build map search links for supported grocery chains near a location."""
    links: list[str] = []
    for _, chain_label in PRICE_CHAINS.items():
        query = quote_plus(f"{chain_label} near {location}")
        links.append(f"{chain_label}: https://www.google.com/maps/search/{query}")
    return links


def _catalog_snapshot_for_chat(db) -> list[dict]:
    """Load the authoritative catalog snapshot used by both chat and prices pages."""
    seed_vegetables(db)
    return list_vegetables(db)


def _build_rag_context(
    db,
    user_id: int,
    user_message: str,
    history: list[dict],
    catalog: list[dict] | None = None,
) -> str:
    """Retrieve catalog, pricing, and user-memory snippets for augmented prompting."""
    if catalog is None:
        catalog = _catalog_snapshot_for_chat(db)
    selected_items = _select_relevant_catalog_items(user_message, catalog, limit=6)
    selected_keys = {str(item.get("key") or "") for item in selected_items}

    memory_lines: list[str] = []
    predictions, _ = list_veggie_predictions(db, user_id=user_id, page=1, page_size=5)
    for prediction in predictions:
        vegetable = str(prediction.get("vegetable") or "")
        if selected_keys and str(prediction.get("key") or "") not in selected_keys:
            continue
        if not vegetable:
            continue
        memory_lines.append(
            f"{vegetable} at {float(prediction.get('confidence') or 0.0):.1f}% "
            f"using {prediction.get('modelName')} ({prediction.get('timestamp')})"
        )
    if not memory_lines:
        memory_lines.append("No recent veggie predictions for this context.")

    recent_turns = [
        f"{item['role']}: {str(item.get('content') or '').strip()}"
        for item in history[-6:]
        if item.get("role") in {"user", "assistant"} and str(item.get("content") or "").strip()
    ]
    if not recent_turns:
        recent_turns.append("No prior conversation turns.")

    if not selected_items:
        selected_items = catalog[:4]

    price_lines = [_format_price_line(item) for item in selected_items]
    nutrition_lines = []
    for item in selected_items:
        nutrients = item.get("nutrients") or []
        nutrients_text = ", ".join(str(nutrient) for nutrient in nutrients[:4]) if nutrients else "N/A"
        nutrition_lines.append(f"{item['name']}: {nutrients_text}")

    location = _latest_user_location(history)
    location_lines: list[str] = []
    if location:
        location_lines.append(f"User-stated location: {location.title()}")
        zone = _infer_zone_from_location(location)
        if zone:
            location_lines.append(f"Inferred zone: {zone.title()}")
        location_lines.append("Store locator links:")
        location_lines.extend(_build_store_locator_links(location))
    else:
        location_lines.append("No user location found in conversation memory.")

    sections = [
        "Retrieved Knowledge:",
        "Catalog and Nutrition:",
        *[f"- {line}" for line in nutrition_lines],
        "Current Prices (SGD):",
        *[f"- {line}" for line in price_lines],
        "Price Intelligence:",
        f"- {_summarize_cheapest_chains(selected_items)}",
        "User Location Context:",
        *[f"- {line}" for line in location_lines],
        "User Prediction Memory:",
        *[f"- {line}" for line in memory_lines],
        "Recent Conversation Memory:",
        *[f"- {line}" for line in recent_turns],
    ]
    return "\n".join(sections)


def _build_openai_messages(history: list[dict], rag_context: str) -> list[dict]:
    """Build an OpenAI chat payload from scoped memory and retrieved context."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "system", "content": rag_context})
    for item in history:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    return messages


def _request_openai_reply(messages: list[dict]) -> str:
    """Call OpenAI chat completions and return assistant text output."""
    api_key = current_app.config.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OpenAI API key is not configured")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": current_app.config["OPENAI_CHAT_MODEL"],
            "messages": messages,
            "temperature": 0.2,
        },
        timeout=current_app.config["OPENAI_TIMEOUT_SEC"],
    )
    if response.status_code >= 400:
        details = response.text
        try:
            details = response.json()
        except ValueError:
            pass
        raise ValueError(f"OpenAI request failed: {details}")

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("OpenAI response did not contain choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise ValueError("OpenAI response did not contain message content")
    return str(content).strip()


@chat_bp.get("/conversations")
@jwt_required
def chat_conversations():
    """Return chat conversation headers for the current user."""
    limit = _parse_limit(request.args.get("limit"), default=30, max_value=200)
    user_id = int(g.user["sub"])
    conversations = list_chat_conversations(get_db(), user_id=user_id, limit=limit)
    return ok_response({"conversations": conversations})


@chat_bp.post("/conversations")
@jwt_required
def chat_create_conversation():
    """Create a new chat conversation for the current user."""
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title") or "").strip() or None
    db = get_db()
    user_id = int(g.user["sub"])
    conversation_id = create_chat_conversation(db, user_id=user_id, title=title)
    conversation = get_chat_conversation(db, user_id=user_id, conversation_id=conversation_id)
    return ok_response({"conversation": conversation}, status=201)


@chat_bp.get("/history")
@jwt_required
def chat_history():
    """Return chat history for the current user."""
    limit = _parse_limit(request.args.get("limit"), default=100, max_value=500)
    try:
        conversation_id = _parse_optional_positive_int(request.args.get("conversation_id"), "conversation_id")
    except ValueError as exc:
        return error_response("validation_error", str(exc))

    db = get_db()
    user_id = int(g.user["sub"])
    conversation = ensure_chat_conversation(
        db,
        user_id=user_id,
        conversation_id=conversation_id,
        create_if_missing=True,
    )
    if conversation_id is not None and not conversation:
        return error_response("not_found", "conversation not found", status=404)
    if not conversation:
        return ok_response({"conversation_id": None, "conversation": None, "messages": []})

    selected_id = int(conversation["id"])
    messages = list_chat_messages(db, user_id=user_id, conversation_id=selected_id, limit=limit)
    return ok_response({"conversation_id": selected_id, "conversation": conversation, "messages": messages})


@chat_bp.delete("/history")
@jwt_required
def chat_clear_history():
    """Delete all chat history for the current user."""
    payload = request.get_json(silent=True) or {}
    raw_conversation = request.args.get("conversation_id", payload.get("conversation_id"))
    try:
        conversation_id = _parse_optional_positive_int(raw_conversation, "conversation_id")
    except ValueError as exc:
        return error_response("validation_error", str(exc))

    db = get_db()
    user_id = int(g.user["sub"])
    if conversation_id is None:
        deleted = clear_chat_messages(db, user_id=user_id)
        return ok_response({"deleted": deleted})

    conversation = get_chat_conversation(db, user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        return error_response("not_found", "conversation not found", status=404)

    deleted = clear_chat_messages(db, user_id=user_id, conversation_id=conversation_id)
    updated_conversation = get_chat_conversation(db, user_id=user_id, conversation_id=conversation_id)
    return ok_response({"deleted": deleted, "conversation_id": conversation_id, "conversation": updated_conversation})


@chat_bp.post("/message")
@jwt_required
def chat_message():
    """Store user message, run scoped retrieval, and return assistant response."""
    payload = request.get_json(silent=True) or {}
    content = str(payload.get("message") or "").strip()
    if not content:
        return error_response("validation_error", "message is required")
    if len(content) > 2000:
        return error_response("validation_error", "message exceeds 2000 characters")
    try:
        conversation_id = _parse_optional_positive_int(payload.get("conversation_id"), "conversation_id")
    except ValueError as exc:
        return error_response("validation_error", str(exc))

    db = get_db()
    user_id = int(g.user["sub"])
    conversation = ensure_chat_conversation(
        db,
        user_id=user_id,
        conversation_id=conversation_id,
        create_if_missing=True,
    )
    if conversation_id is not None and not conversation:
        return error_response("not_found", "conversation not found", status=404)
    if not conversation:
        return error_response("service_error", "Unable to initialize chat conversation", status=500)
    active_conversation_id = int(conversation["id"])

    insert_chat_message(
        db,
        user_id=user_id,
        conversation_id=active_conversation_id,
        role="user",
        content=content,
    )
    history = list_recent_chat_messages(
        db,
        user_id=user_id,
        conversation_id=active_conversation_id,
        limit=20,
    )
    catalog = _catalog_snapshot_for_chat(db)

    if not _is_vegetable_related(content, catalog, history):
        message_id = insert_chat_message(
            db,
            user_id=user_id,
            conversation_id=active_conversation_id,
            role="assistant",
            content=OUT_OF_SCOPE_REPLY,
        )
        updated_conversation = get_chat_conversation(db, user_id=user_id, conversation_id=active_conversation_id)
        return ok_response(
            {
                "conversation_id": active_conversation_id,
                "conversation": updated_conversation,
                "message": {
                    "id": message_id,
                    "conversation_id": active_conversation_id,
                    "role": "assistant",
                    "content": OUT_OF_SCOPE_REPLY,
                },
                "guardrail": {"scope_restricted": True},
            }
        )

    rag_context = _build_rag_context(
        db,
        user_id=user_id,
        user_message=content,
        history=history,
        catalog=catalog,
    )
    messages = _build_openai_messages(history, rag_context)

    try:
        reply = _request_openai_reply(messages)
    except RuntimeError as exc:
        return error_response("service_unavailable", str(exc), status=503)
    except requests.RequestException as exc:
        logger.warning("openai_request_exception user_id=%s error=%s", user_id, str(exc))
        return error_response("service_unavailable", "OpenAI service unavailable", details=str(exc), status=503)
    except ValueError as exc:
        logger.warning("openai_response_error user_id=%s error=%s", user_id, str(exc))
        return error_response("service_error", "OpenAI request failed", details=str(exc), status=502)

    message_id = insert_chat_message(
        db,
        user_id=user_id,
        conversation_id=active_conversation_id,
        role="assistant",
        content=reply,
    )
    updated_conversation = get_chat_conversation(db, user_id=user_id, conversation_id=active_conversation_id)
    return ok_response(
        {
            "conversation_id": active_conversation_id,
            "conversation": updated_conversation,
            "message": {
                "id": message_id,
                "conversation_id": active_conversation_id,
                "role": "assistant",
                "content": reply,
            },
        }
    )
