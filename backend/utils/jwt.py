"""JWT helpers and decorator."""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, request, session
from jwt import ExpiredSignatureError, InvalidTokenError

from .responses import error_response


def create_token(user_id: int, username: str, role: str) -> str:
    """Create a signed JWT token for an authenticated user."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=current_app.config["JWT_EXPIRES_MINUTES"])
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    return jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])


def _session_jwt_payload() -> dict | None:
    """Return decoded session JWT payload when available and consistent."""
    session_token = str(session.get("token") or "").strip()
    session_user = session.get("user") or {}
    if not session_token or not isinstance(session_user, dict):
        return None
    try:
        payload = decode_token(session_token)
    except (ExpiredSignatureError, InvalidTokenError):
        return None

    session_user_id = str(session_user.get("id") or "").strip()
    payload_user_id = str(payload.get("sub") or "").strip()
    if not session_user_id or not payload_user_id or session_user_id != payload_user_id:
        return None
    return payload


def jwt_required(fn=None, *, allow_query_token: bool = False, allow_session_user: bool = False):
    """Protect a route by requiring a valid JWT token."""

    def decorator(func):
        """Wrap a Flask view with JWT authentication checks."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Validate token from header (or query string if explicitly allowed)."""
            token = None
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                token = auth.split(" ", 1)[1].strip()
            if not token and allow_query_token:
                token = request.args.get("token")

            if not token and allow_session_user:
                payload = _session_jwt_payload()
                if payload:
                    g.user = payload
                    return func(*args, **kwargs)

            if not token:
                return error_response("unauthorized", "Missing token", status=401)
            try:
                payload = decode_token(token)
            except ExpiredSignatureError:
                if allow_session_user:
                    fallback = _session_jwt_payload()
                    if fallback:
                        g.user = fallback
                        return func(*args, **kwargs)
                return error_response("token_expired", "Token expired", status=401)
            except InvalidTokenError:
                if allow_session_user:
                    fallback = _session_jwt_payload()
                    if fallback:
                        g.user = fallback
                        return func(*args, **kwargs)
                return error_response("invalid_token", "Invalid token", status=401)
            g.user = payload
            return func(*args, **kwargs)

        return wrapper

    if fn is None:
        return decorator
    return decorator(fn)
