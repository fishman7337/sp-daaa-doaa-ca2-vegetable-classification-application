"""Flask + Jinja page routes with session-backed auth."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, redirect, render_template, request, send_from_directory, session, url_for
from jwt import ExpiredSignatureError, InvalidTokenError

from .db import get_db
from .repository import get_user_by_id
from .utils.jwt import decode_token
from .utils.responses import error_response, ok_response

views_bp = Blueprint("views", __name__)


def _session_user_payload(user: dict[str, Any]) -> dict[str, Any]:
    """Build a safe session payload from a database user row.

    Args:
        user: Raw user payload loaded from the repository layer.

    Returns:
        dict[str, Any]: Session-ready user fields used by templates.
    """
    username = user.get("username")
    email = user.get("email")
    display_name = user.get("display_name") or username or "User"
    avatar = user.get("avatar")
    if not avatar and (email or username):
        avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={email or username}"
    return {
        "id": str(user["id"]),
        "username": username,
        "name": display_name,
        "email": email,
        "role": user.get("role", "user"),
        "avatar": avatar,
    }


def _require_login():
    """Enforce authenticated session access for protected pages.

    Returns:
        Response | None: Redirect response to `/auth` when unauthenticated, else `None`.
    """
    user = session.get("user")
    token = session.get("token")
    if not user or not token:
        return redirect(url_for("views.auth_page", next=request.path))

    try:
        claims = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        session.clear()
        return redirect(url_for("views.auth_page", next=request.path))

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        session.clear()
        return redirect(url_for("views.auth_page", next=request.path))

    db = get_db()
    user_row = get_user_by_id(db, user_id)
    if not user_row:
        session.clear()
        return redirect(url_for("views.auth_page", next=request.path))

    session["user"] = _session_user_payload(user_row)
    return None


@views_bp.get("/")
def home():
    """Render the public homepage."""
    return render_template("home.html", active_page="home", page_id="home")


@views_bp.get("/auth")
def auth_page():
    """Render the authentication page."""
    if session.get("user") and session.get("token"):
        return redirect(url_for("views.predict_page"))
    return render_template("auth.html", active_page="auth", page_id="auth")


@views_bp.get("/predict")
def predict_page():
    """Render the protected classify page."""
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response
    return render_template("predict.html", active_page="predict", page_id="predict")


@views_bp.get("/prices")
def prices_page():
    """Render the protected pricing page."""
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response
    return render_template("prices.html", active_page="prices", page_id="prices")


@views_bp.get("/profile")
def profile_page():
    """Render the protected profile page."""
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response
    return render_template("profile.html", active_page="profile", page_id="profile")


@views_bp.get("/history")
def history_page():
    """Redirect protected history route to classify page history tab."""
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response
    return redirect(url_for("views.predict_page", tab="history"))


@views_bp.post("/web/session/login")
def session_login():
    """Create a Flask session from a valid JWT token."""
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    if not token:
        return error_response("validation_error", "token is required", status=400)

    try:
        claims = decode_token(token)
    except ExpiredSignatureError:
        return error_response("token_expired", "Token expired", status=401)
    except InvalidTokenError:
        return error_response("invalid_token", "Invalid token", status=401)

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        return error_response("invalid_token", "Invalid token payload", status=401)

    db = get_db()
    user_row = get_user_by_id(db, user_id)
    if not user_row:
        return error_response("not_found", "User not found", status=404)

    session["token"] = token
    session["user"] = _session_user_payload(user_row)
    session.modified = True
    return ok_response({"authenticated": True, "user": session["user"]})


@views_bp.post("/web/session/logout")
def session_logout():
    """Clear the current Flask session."""
    session.clear()
    return ok_response({"logged_out": True})


@views_bp.route("/web/theme", methods=["GET", "POST"])
def session_theme():
    """Persist a user theme preference for server-rendered pages."""
    if request.method == "GET":
        cookie_theme = (request.cookies.get("veggie-theme") or "").strip().lower()
        session_theme_value = str(session.get("theme") or "").strip().lower()
        theme = (
            session_theme_value
            if session_theme_value in {"light", "dark"}
            else cookie_theme
            if cookie_theme in {"light", "dark"}
            else "dark"
        )
        return ok_response({"theme": theme})

    payload = request.get_json(silent=True) or {}
    theme = str(payload.get("theme") or "").strip().lower()
    if theme not in {"light", "dark"}:
        return error_response("validation_error", "theme must be 'light' or 'dark'", status=400)

    session["theme"] = theme
    session.modified = True
    response, status_code = ok_response({"theme": theme})
    response.set_cookie(
        "veggie-theme",
        theme,
        max_age=31536000,
        samesite="Lax",
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE", False)),
        httponly=False,
        path="/",
    )
    return response, status_code


@views_bp.get("/logout")
def logout():
    """Legacy logout route for browser navigation."""
    session.clear()
    return redirect(url_for("views.home"))


@views_bp.get("/web/logout")
def legacy_logout():
    """Legacy web logout route maintained for backward compatibility."""
    session.clear()
    return redirect(url_for("views.home"))


@views_bp.get("/web/login")
def legacy_login():
    """Legacy web login route redirected to the unified auth page."""
    return redirect(url_for("views.auth_page"))


@views_bp.get("/web/register")
def legacy_register():
    """Legacy web register route redirected to the unified auth page."""
    return redirect(url_for("views.auth_page"))


@views_bp.get("/web/predict")
def legacy_predict():
    """Legacy web predict route redirected to the protected classify page."""
    return redirect(url_for("views.predict_page"))


@views_bp.get("/web/history")
def legacy_history():
    """Legacy web history route redirected to the history tab."""
    return redirect(url_for("views.history_page"))


@views_bp.get("/favicon.ico")
def favicon_ico():
    """Serve the site favicon path expected by browsers like Chrome."""
    static_dir = Path(current_app.static_folder or ".")
    response = send_from_directory(
        str(static_dir / "images"),
        "favicon-leaf.ico",
        mimetype="image/x-icon",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
