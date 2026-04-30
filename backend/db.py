"""SQLite helpers for backend storage."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """Execute table columns."""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    """Execute ensure column."""
    if column_name in _table_columns(conn, table_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def _run_migrations(conn: sqlite3.Connection) -> None:
    # Older DB files may not have these profile columns.
    """Execute run migrations."""
    _ensure_column(conn, "users", "email", "email TEXT")
    _ensure_column(conn, "users", "display_name", "display_name TEXT")
    _ensure_column(conn, "users", "avatar", "avatar TEXT")
    _ensure_column(conn, "veggie_predictions", "model_name", "model_name TEXT NOT NULL DEFAULT 'vegnet-23'")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New chat',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_message_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            conversation_id INTEGER,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE
        )
        """
    )
    _ensure_column(conn, "chat_messages", "conversation_id", "conversation_id INTEGER")

    rows = conn.execute(
        """
        SELECT id, user_id
        FROM chat_messages
        WHERE conversation_id IS NULL
        ORDER BY user_id ASC, id ASC
        """
    ).fetchall()
    if rows:
        conversation_by_user: dict[int, int] = {}
        for row in rows:
            message_id = int(row[0])
            user_id = int(row[1])
            conversation_id = conversation_by_user.get(user_id)
            if conversation_id is None:
                existing = conn.execute(
                    """
                    SELECT id
                    FROM chat_conversations
                    WHERE user_id = ?
                    ORDER BY last_message_at DESC, id DESC
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
                if existing:
                    conversation_id = int(existing[0])
                else:
                    cursor = conn.execute(
                        """
                        INSERT INTO chat_conversations (user_id, title)
                        VALUES (?, 'Imported chat')
                        """,
                        (user_id,),
                    )
                    conversation_id = int(cursor.lastrowid)
                conversation_by_user[user_id] = conversation_id

            conn.execute(
                "UPDATE chat_messages SET conversation_id = ? WHERE id = ?",
                (conversation_id, message_id),
            )

    conn.execute(
        """
        UPDATE chat_conversations
        SET
            last_message_at = COALESCE(
                (SELECT MAX(created_at) FROM chat_messages WHERE conversation_id = chat_conversations.id),
                last_message_at
            ),
            updated_at = COALESCE(
                (SELECT MAX(created_at) FROM chat_messages WHERE conversation_id = chat_conversations.id),
                updated_at
            )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS captcha_challenges (
            id TEXT PRIMARY KEY,
            answer_hash TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS otp_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            purpose TEXT NOT NULL,
            email TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            consumed_at INTEGER,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_veggie_predictions_model_name ON veggie_predictions(model_name)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_last_message "
        "ON chat_conversations(user_id, last_message_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created ON chat_messages(user_id, created_at)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_user_conversation_created "
        "ON chat_messages(user_id, conversation_id, created_at)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_captcha_challenges_expires ON captcha_challenges(expires_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_otp_sessions_user_id ON otp_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_otp_sessions_expires ON otp_sessions(expires_at)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL")


def get_db() -> sqlite3.Connection:
    """Return a per-request SQLite connection."""
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(error=None) -> None:
    """Close the SQLite connection at request end."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path: str, schema_path: str, force: bool = False) -> None:
    """Initialize the SQLite database from schema."""
    path = Path(db_path)
    if force and path.exists():
        path.unlink()
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    with open(schema_path, "r", encoding="utf-8") as handle:
        conn.executescript(handle.read())
    _run_migrations(conn)
    conn.commit()
    conn.close()
