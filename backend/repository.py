"""Repository layer for user and prediction queries."""

from __future__ import annotations

import json

from .utils.search import build_where_clause
from .veggie_catalog import VEGETABLE_CATALOG, serialize_catalog_item


def row_to_dict(row) -> dict:
    """Execute row to dict."""
    return dict(row) if row else {}


def create_user(
    db,
    username: str,
    password_hash: str,
    role: str = "user",
    email: str | None = None,
    display_name: str | None = None,
    avatar: str | None = None,
) -> int:
    """Execute create user."""
    cursor = db.execute(
        """
        INSERT INTO users (username, password_hash, role, email, display_name, avatar)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, password_hash, role, email, display_name, avatar),
    )
    db.commit()
    return cursor.lastrowid


def get_user_by_username(db, username: str):
    """Execute get user by username."""
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return row_to_dict(row) if row else None


def get_user_by_email(db, email: str):
    """Execute get user by email."""
    row = db.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
    return row_to_dict(row) if row else None


def get_user_by_id(db, user_id: int):
    """Execute get user by id."""
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_dict(row) if row else None


def delete_user_by_id(db, user_id: int) -> bool:
    """Delete one user row by id and return whether a record was removed."""
    cursor = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return cursor.rowcount > 0


def update_user_profile(
    db,
    user_id: int,
    *,
    display_name: str | None = None,
    email: str | None = None,
    avatar: str | None = None,
) -> None:
    """Execute update user profile."""
    has_display_name = display_name is not None
    has_email = email is not None
    has_avatar = avatar is not None
    if not (has_display_name or has_email or has_avatar):
        return
    db.execute(
        """
        UPDATE users
        SET
            display_name = CASE WHEN ? THEN ? ELSE display_name END,
            email = CASE WHEN ? THEN ? ELSE email END,
            avatar = CASE WHEN ? THEN ? ELSE avatar END
        WHERE id = ?
        """,
        (
            has_display_name,
            display_name,
            has_email,
            email,
            has_avatar,
            avatar,
            user_id,
        ),
    )
    db.commit()


def update_user_password_hash(db, user_id: int, password_hash: str) -> None:
    """Execute update user password hash."""
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    db.commit()


def update_last_login(db, user_id: int) -> None:
    """Execute update last login."""
    db.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user_id,))
    db.commit()


def insert_prediction(db, payload: dict) -> int:
    """Execute insert prediction."""
    cursor = db.execute(
        """
        INSERT INTO predictions (
            user_id, model_name, input_type, input_ref, sha256,
            top1_label, top1_conf, topk_json, latency_ms, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["user_id"],
            payload["model_name"],
            payload["input_type"],
            payload["input_ref"],
            payload["sha256"],
            payload["top1_label"],
            payload["top1_conf"],
            payload["topk_json"],
            payload["latency_ms"],
            payload.get("notes"),
        ),
    )
    db.commit()
    return cursor.lastrowid


def get_prediction_by_id(db, prediction_id: int, user_id: int):
    """Execute get prediction by id."""
    row = db.execute(
        """
        SELECT p.*, u.username
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ? AND p.user_id = ?
        """,
        (prediction_id, user_id),
    ).fetchone()
    if not row:
        return None
    data = row_to_dict(row)
    data["topk"] = json.loads(data.get("topk_json") or "[]")
    return data


def delete_prediction(db, prediction_id: int, user_id: int) -> bool:
    """Execute delete prediction."""
    cursor = db.execute("DELETE FROM predictions WHERE id = ? AND user_id = ?", (prediction_id, user_id))
    db.commit()
    return cursor.rowcount > 0


def search_predictions(
    db,
    user_id: int,
    search_text: str,
    filters: dict,
    page: int,
    page_size: int,
    sort: str,
):
    """Execute search predictions."""
    where_sql, params = build_where_clause(search_text, filters)
    params = list(params)
    if where_sql:
        where_sql = f"{where_sql} AND p.user_id = ?"
    else:
        where_sql = " WHERE p.user_id = ?"
    params.append(user_id)

    base_sql = "FROM predictions p JOIN users u ON p.user_id = u.id"
    count_sql = f"SELECT COUNT(*) {base_sql}{where_sql}"
    total = db.execute(count_sql, params).fetchone()[0]

    order_by = {
        "newest": "p.created_at DESC",
        "oldest": "p.created_at ASC",
        "confidence_desc": "p.top1_conf DESC",
        "latency_asc": "p.latency_ms ASC",
    }.get(sort, "p.created_at DESC")

    offset = (page - 1) * page_size
    data_sql = f"SELECT p.*, u.username {base_sql}{where_sql} ORDER BY {order_by} LIMIT ? OFFSET ?"
    rows = db.execute(data_sql, params + [page_size, offset]).fetchall()
    results = []
    for row in rows:
        item = row_to_dict(row)
        item["topk"] = json.loads(item.get("topk_json") or "[]")
        results.append(item)
    return results, total


def seed_vegetables(db) -> None:
    """Execute seed vegetables."""
    for key, item in VEGETABLE_CATALOG.items():
        db.execute(
            """
            INSERT INTO vegetables (
                key, name, scientific_name, category, description, nutrients_json,
                unit, seasonality, storage_life, price_ntuc, price_giant,
                price_cold_storage, price_sheng_siong
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                name = excluded.name,
                scientific_name = excluded.scientific_name,
                category = excluded.category,
                description = excluded.description,
                nutrients_json = excluded.nutrients_json,
                unit = excluded.unit,
                seasonality = excluded.seasonality,
                storage_life = excluded.storage_life,
                price_ntuc = excluded.price_ntuc,
                price_giant = excluded.price_giant,
                price_cold_storage = excluded.price_cold_storage,
                price_sheng_siong = excluded.price_sheng_siong
            """,
            (
                key,
                item["name"],
                item["scientificName"],
                item["category"],
                item["description"],
                json.dumps(item["nutrients"]),
                item["unit"],
                item.get("seasonality"),
                item.get("storageLife"),
                item["prices"]["ntuc"],
                item["prices"]["giant"],
                item["prices"]["coldStorage"],
                item["prices"]["shengSiong"],
            ),
        )
    db.commit()


def _vegetable_row_to_payload(row) -> dict:
    """Execute vegetable row to payload."""
    payload = {
        "key": row["key"],
        "name": row["name"],
        "scientificName": row["scientific_name"],
        "category": row["category"],
        "description": row["description"],
        "nutrients": json.loads(row["nutrients_json"] or "[]"),
        "unit": row["unit"],
        "seasonality": row["seasonality"],
        "storageLife": row["storage_life"],
        "prices": {
            "ntuc": float(row["price_ntuc"]),
            "giant": float(row["price_giant"]),
            "coldStorage": float(row["price_cold_storage"]),
            "shengSiong": float(row["price_sheng_siong"]),
        },
    }
    return serialize_catalog_item(payload)


def list_vegetables(db) -> list[dict]:
    """Execute list vegetables."""
    rows = db.execute("SELECT * FROM vegetables ORDER BY name ASC").fetchall()
    return [_vegetable_row_to_payload(row) for row in rows]


def get_vegetable_by_key(db, key: str):
    """Execute get vegetable by key."""
    row = db.execute("SELECT * FROM vegetables WHERE key = ?", (key,)).fetchone()
    if not row:
        return None
    return _vegetable_row_to_payload(row)


def insert_veggie_prediction(
    db,
    prediction_id: str,
    user_id: int,
    image_ref: str,
    image_sha256: str,
    model_name: str,
    vegetable_key: str,
    confidence: float,
) -> None:
    """Execute insert veggie prediction."""
    db.execute(
        """
        INSERT INTO veggie_predictions (id, user_id, image_ref, image_sha256, model_name, vegetable_key, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (prediction_id, user_id, image_ref, image_sha256, model_name, vegetable_key, confidence),
    )
    db.commit()


def _veggie_prediction_row_to_payload(row) -> dict:
    """Execute veggie prediction row to payload."""
    return {
        "id": row["id"],
        "imageRef": row["image_ref"],
        "imageSha256": row["image_sha256"],
        "modelName": row["model_name"],
        "key": row["vegetable_key"],
        "confidence": float(row["confidence"]),
        "timestamp": row["created_at"],
        "vegetable": row["name"],
        "scientificName": row["scientific_name"],
        "category": row["category"],
        "prices": {
            "ntuc": float(row["price_ntuc"]),
            "giant": float(row["price_giant"]),
            "coldStorage": float(row["price_cold_storage"]),
            "shengSiong": float(row["price_sheng_siong"]),
        },
    }


def list_veggie_predictions(db, user_id: int, page: int, page_size: int):
    """Execute list veggie predictions."""
    total = db.execute(
        "SELECT COUNT(*) FROM veggie_predictions WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = db.execute(
        """
        SELECT vp.*, v.name, v.scientific_name, v.category,
               v.price_ntuc, v.price_giant, v.price_cold_storage, v.price_sheng_siong
        FROM veggie_predictions vp
        JOIN vegetables v ON vp.vegetable_key = v.key
        WHERE vp.user_id = ?
        ORDER BY vp.created_at DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, page_size, offset),
    ).fetchall()
    return [_veggie_prediction_row_to_payload(row) for row in rows], total


def get_veggie_prediction(db, user_id: int, prediction_id: str):
    """Execute get veggie prediction."""
    row = db.execute(
        """
        SELECT vp.*, v.name, v.scientific_name, v.category,
               v.price_ntuc, v.price_giant, v.price_cold_storage, v.price_sheng_siong
        FROM veggie_predictions vp
        JOIN vegetables v ON vp.vegetable_key = v.key
        WHERE vp.user_id = ? AND vp.id = ?
        """,
        (user_id, prediction_id),
    ).fetchone()
    if not row:
        return None
    return _veggie_prediction_row_to_payload(row)


def delete_veggie_prediction(db, user_id: int, prediction_id: str) -> bool:
    """Execute delete veggie prediction."""
    cursor = db.execute(
        "DELETE FROM veggie_predictions WHERE user_id = ? AND id = ?",
        (user_id, prediction_id),
    )
    db.commit()
    return cursor.rowcount > 0


def clear_veggie_predictions(db, user_id: int) -> int:
    """Execute clear veggie predictions."""
    cursor = db.execute("DELETE FROM veggie_predictions WHERE user_id = ?", (user_id,))
    db.commit()
    return cursor.rowcount


def _normalize_chat_title(value: str, limit: int = 64) -> str:
    """Normalize user input into a compact, single-line conversation title."""
    text = " ".join(str(value or "").strip().split())
    if not text:
        return "New chat"
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}..."


def _chat_conversation_row_to_payload(row) -> dict:
    """Convert one `chat_conversations` row to API payload format."""
    message_count = row["message_count"] if "message_count" in row.keys() else 0
    return {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_message_at": row["last_message_at"],
        "message_count": int(message_count or 0),
    }


def create_chat_conversation(db, user_id: int, title: str | None = None) -> int:
    """Create and persist a new chat conversation for one authenticated user."""
    normalized_title = _normalize_chat_title(title or "New chat")
    cursor = db.execute(
        """
        INSERT INTO chat_conversations (user_id, title)
        VALUES (?, ?)
        """,
        (user_id, normalized_title),
    )
    db.commit()
    return cursor.lastrowid


def get_chat_conversation(db, user_id: int, conversation_id: int):
    """Fetch one conversation by owner and identifier."""
    row = db.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at, c.last_message_at,
               COUNT(m.id) AS message_count
        FROM chat_conversations c
        LEFT JOIN chat_messages m ON m.conversation_id = c.id
        WHERE c.user_id = ? AND c.id = ?
        GROUP BY c.id
        """,
        (user_id, conversation_id),
    ).fetchone()
    return _chat_conversation_row_to_payload(row) if row else None


def get_latest_chat_conversation(db, user_id: int):
    """Fetch the newest conversation for one user ordered by last activity."""
    row = db.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at, c.last_message_at,
               COUNT(m.id) AS message_count
        FROM chat_conversations c
        LEFT JOIN chat_messages m ON m.conversation_id = c.id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.last_message_at DESC, c.id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return _chat_conversation_row_to_payload(row) if row else None


def ensure_chat_conversation(
    db,
    user_id: int,
    conversation_id: int | None = None,
    *,
    create_if_missing: bool = True,
):
    """Resolve a valid conversation for one user, optionally creating a default."""
    if conversation_id is not None:
        return get_chat_conversation(db, user_id, conversation_id)

    conversation = get_latest_chat_conversation(db, user_id)
    if conversation or not create_if_missing:
        return conversation

    created_id = create_chat_conversation(db, user_id, title="New chat")
    return get_chat_conversation(db, user_id, created_id)


def list_chat_conversations(db, user_id: int, limit: int = 50) -> list[dict]:
    """List recent conversations for one user with message counts."""
    rows = db.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at, c.last_message_at,
               COUNT(m.id) AS message_count
        FROM chat_conversations c
        LEFT JOIN chat_messages m ON m.conversation_id = c.id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.last_message_at DESC, c.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [_chat_conversation_row_to_payload(row) for row in rows]


def insert_chat_message(db, user_id: int, conversation_id: int, role: str, content: str) -> int:
    """Insert one chat message in the selected conversation and update metadata."""
    cursor = db.execute(
        """
        INSERT INTO chat_messages (user_id, conversation_id, role, content)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, conversation_id, role, content),
    )
    db.execute(
        """
        UPDATE chat_conversations
        SET updated_at = datetime('now'), last_message_at = datetime('now')
        WHERE id = ? AND user_id = ?
        """,
        (conversation_id, user_id),
    )

    if role == "user":
        title_row = db.execute(
            "SELECT title FROM chat_conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        first_user_count = db.execute(
            """
            SELECT COUNT(*)
            FROM chat_messages
            WHERE conversation_id = ? AND user_id = ? AND role = 'user'
            """,
            (conversation_id, user_id),
        ).fetchone()[0]
        current_title = str((title_row["title"] if title_row else "") or "").strip().lower()
        if first_user_count == 1 and current_title in {"new chat", "imported chat"}:
            db.execute(
                "UPDATE chat_conversations SET title = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?",
                (_normalize_chat_title(content), conversation_id, user_id),
            )

    db.commit()
    return cursor.lastrowid


def list_chat_messages(db, user_id: int, conversation_id: int, limit: int = 100) -> list[dict]:
    """List ordered chat messages within one conversation."""
    rows = db.execute(
        """
        SELECT id, conversation_id, role, content, created_at
        FROM chat_messages
        WHERE user_id = ? AND conversation_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (user_id, conversation_id, limit),
    ).fetchall()
    ordered = list(reversed(rows))
    return [
        {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "timestamp": row["created_at"],
        }
        for row in ordered
    ]


def list_recent_chat_messages(db, user_id: int, conversation_id: int, limit: int = 20) -> list[dict]:
    """List the latest window of conversation messages for context retrieval."""
    rows = db.execute(
        """
        SELECT id, conversation_id, role, content, created_at
        FROM chat_messages
        WHERE user_id = ? AND conversation_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (user_id, conversation_id, limit),
    ).fetchall()
    ordered = list(reversed(rows))
    return [
        {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "timestamp": row["created_at"],
        }
        for row in ordered
    ]


def clear_chat_messages(db, user_id: int, conversation_id: int | None = None) -> int:
    """Clear chat messages for one user, optionally scoped to one conversation."""
    if conversation_id is None:
        cursor = db.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        db.execute(
            """
            UPDATE chat_conversations
            SET updated_at = datetime('now'), last_message_at = datetime('now')
            WHERE user_id = ?
            """,
            (user_id,),
        )
    else:
        cursor = db.execute(
            "DELETE FROM chat_messages WHERE user_id = ? AND conversation_id = ?",
            (user_id, conversation_id),
        )
        db.execute(
            """
            UPDATE chat_conversations
            SET
                updated_at = datetime('now'),
                last_message_at = COALESCE(
                    (
                        SELECT MAX(created_at)
                        FROM chat_messages
                        WHERE conversation_id = chat_conversations.id
                    ),
                    datetime('now')
                )
            WHERE id = ? AND user_id = ?
            """,
            (conversation_id, user_id),
        )
    db.commit()
    return cursor.rowcount


def prune_expired_captcha_challenges(db, now_epoch: int) -> None:
    """Execute prune expired captcha challenges."""
    db.execute("DELETE FROM captcha_challenges WHERE expires_at <= ?", (now_epoch,))
    db.commit()


def create_captcha_challenge(db, captcha_id: str, answer_hash: str, created_at: int, expires_at: int) -> None:
    """Execute create captcha challenge."""
    db.execute(
        """
        INSERT INTO captcha_challenges (id, answer_hash, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (captcha_id, answer_hash, expires_at, created_at),
    )
    db.commit()


def get_captcha_challenge(db, captcha_id: str):
    """Execute get captcha challenge."""
    row = db.execute(
        "SELECT id, answer_hash, expires_at, created_at FROM captcha_challenges WHERE id = ?",
        (captcha_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def delete_captcha_challenge(db, captcha_id: str) -> None:
    """Execute delete captcha challenge."""
    db.execute("DELETE FROM captcha_challenges WHERE id = ?", (captcha_id,))
    db.commit()


def create_otp_session(
    db,
    session_id: str,
    user_id: int,
    purpose: str,
    email: str,
    otp_hash: str,
    max_attempts: int,
    created_at: int,
    expires_at: int,
) -> None:
    """Execute create otp session."""
    db.execute(
        """
        INSERT INTO otp_sessions (
            session_id, user_id, purpose, email, otp_hash,
            attempts, max_attempts, expires_at, consumed_at, created_at
        ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, NULL, ?)
        """,
        (session_id, user_id, purpose, email, otp_hash, max_attempts, expires_at, created_at),
    )
    db.commit()


def get_otp_session(db, session_id: str):
    """Execute get otp session."""
    row = db.execute(
        """
        SELECT session_id, user_id, purpose, email, otp_hash, attempts, max_attempts, expires_at, consumed_at, created_at
        FROM otp_sessions
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def update_otp_session_attempts(db, session_id: str, attempts: int) -> None:
    """Execute update otp session attempts."""
    db.execute("UPDATE otp_sessions SET attempts = ? WHERE session_id = ?", (attempts, session_id))
    db.commit()


def update_otp_session_code(db, session_id: str, otp_hash: str, expires_at: int) -> None:
    """Execute update otp session code."""
    db.execute(
        """
        UPDATE otp_sessions
        SET otp_hash = ?, expires_at = ?, attempts = 0, consumed_at = NULL
        WHERE session_id = ?
        """,
        (otp_hash, expires_at, session_id),
    )
    db.commit()


def consume_otp_session(db, session_id: str, consumed_at: int) -> None:
    """Execute consume otp session."""
    db.execute("UPDATE otp_sessions SET consumed_at = ? WHERE session_id = ?", (consumed_at, session_id))
    db.commit()


def delete_otp_session(db, session_id: str) -> None:
    """Execute delete otp session."""
    db.execute("DELETE FROM otp_sessions WHERE session_id = ?", (session_id,))
    db.commit()


def prune_expired_otp_sessions(db, now_epoch: int) -> None:
    """Execute prune expired otp sessions."""
    db.execute("DELETE FROM otp_sessions WHERE expires_at <= ?", (now_epoch,))
    db.commit()
