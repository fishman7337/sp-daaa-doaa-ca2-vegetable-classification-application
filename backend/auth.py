"""Authentication routes for JWT login, captcha, and OTP verification."""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import math
import mimetypes
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, current_app, g, request, send_file, url_for
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pydantic import ValidationError
from werkzeug.datastructures import MultiDict

from .db import get_db
from .forms import LoginForm, RegisterForm
from .repository import (
    consume_otp_session,
    create_captcha_challenge,
    create_otp_session,
    create_user,
    delete_captcha_challenge,
    delete_otp_session,
    delete_user_by_id,
    get_captcha_challenge,
    get_otp_session,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    prune_expired_captcha_challenges,
    prune_expired_otp_sessions,
    update_last_login,
    update_otp_session_attempts,
    update_otp_session_code,
    update_user_password_hash,
    update_user_profile,
)
from .schemas import (
    LoginRequest,
    OtpResendRequest,
    OtpVerifyRequest,
    PasswordChangeRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from .utils.files import resolve_uploaded_file_path
from .utils.jwt import create_token, jwt_required
from .utils.logging import log_event
from .utils.mailer import send_otp_email, send_password_reset_email
from .utils.rate_limiter import LoginRateLimiter
from .utils.responses import error_response, ok_response
from .utils.security import hash_password, verify_password
from .utils.validation import read_image_bytes

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
CAPTCHA_ALPHABET = "23456789"
DEV_BYPASS_CODE = "00000"


def _safe_validation_errors(exc: ValidationError) -> list[dict]:
    """Return JSON-safe Pydantic validation errors for API responses."""
    return exc.errors(include_url=False, include_context=False, include_input=False)


def _json_to_form_data(payload: dict) -> MultiDict:
    """Convert JSON payload values into WTForms-compatible formdata."""
    form_data: MultiDict = MultiDict()
    for key, value in (payload or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            form_data.add(key, "y" if value else "")
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                if item is None:
                    continue
                form_data.add(key, str(item))
            continue
        form_data.add(key, str(value))
    return form_data


def _format_user_payload(user: dict) -> dict:
    """Execute format user payload."""
    username = user.get("username")
    email = user.get("email")
    display_name = user.get("display_name") or username
    avatar = user.get("avatar") or (
        f"https://api.dicebear.com/7.x/avataaars/svg?seed={email or username}" if (email or username) else None
    )
    return {
        "id": str(user["id"]),
        "username": username,
        "name": display_name,
        "email": email,
        "role": user["role"],
        "avatar": avatar,
    }


def _username_from_email(email: str) -> str:
    """Execute username from email."""
    local = (email.split("@", 1)[0] if email else "user").strip().lower()
    normalized = re.sub(r"[^a-z0-9_.-]+", "", local)
    return normalized[:50] or "user"


def _get_limiter() -> LoginRateLimiter:
    """Execute get limiter."""
    limiter = current_app.extensions.get("login_rate_limiter")
    if limiter is None:
        limiter = LoginRateLimiter(
            current_app.config["RATE_LIMIT_MAX"],
            current_app.config["RATE_LIMIT_WINDOW_SEC"],
        )
        current_app.extensions["login_rate_limiter"] = limiter
    return limiter


def _hash_secret(value: str) -> str:
    """Execute hash secret."""
    token = f"{value}:{current_app.config['SECRET_KEY']}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _mask_email(email: str) -> str:
    """Execute mask email."""
    if "@" not in email:
        return "***"
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked_name = f"{name[:1]}*"
    else:
        masked_name = f"{name[:2]}{'*' * (len(name) - 2)}"
    return f"{masked_name}@{domain}"


def _normalize_email(email: str | None) -> str | None:
    """Execute normalize email."""
    normalized = (email or "").strip().lower()
    return normalized or None


def _normalize_captcha_text(value: str) -> str:
    """Execute normalize captcha text."""
    return "".join(ch for ch in value.strip().upper() if ch.isalnum())


def _is_dev_bypass_code(value: str | None, *, config_flag: str) -> bool:
    """Allow explicit fixed-code bypass only when the corresponding dev flag is enabled."""
    if not current_app.config.get(config_flag):
        return False
    return (value or "").strip() == DEV_BYPASS_CODE


def _generate_captcha_code(length: int) -> str:
    """Execute generate captcha code."""
    _ = length  # Captcha is fixed to 5 characters for consistency and usability.
    size = 5
    picker = secrets.SystemRandom()
    return "".join(picker.choice(CAPTCHA_ALPHABET) for _ in range(size))


def _load_captcha_font(size: int):
    """Execute load captcha font."""
    for font_name in (
        "DejaVuSansMono-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "Arial Bold.ttf",
        "Arial.ttf",
        "LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _resolve_image_mimetype(file_path: Path) -> str:
    """Resolve a concrete image MIME type for file responses."""
    guessed, _ = mimetypes.guess_type(file_path.name)
    if isinstance(guessed, str) and guessed.startswith("image/"):
        return guessed
    return "image/jpeg"


def _delete_avatar_file_if_local(avatar_path: str | None) -> None:
    """Delete an uploaded avatar file if the stored path points to local uploads."""
    if not avatar_path:
        return
    prefix = "/api/auth/avatar/"
    raw_path = str(avatar_path).strip()
    if not raw_path.startswith(prefix):
        return
    filename = raw_path[len(prefix) :].strip()
    if not filename:
        return

    avatars_dir = Path(current_app.config["UPLOAD_DIR"]).expanduser().resolve() / "avatars"
    file_path = resolve_uploaded_file_path(avatars_dir, filename)
    if not file_path:
        return
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("avatar_cleanup_failed filename=%s", filename)


def _random_rgb(picker: secrets.SystemRandom, low: int, high: int) -> tuple[int, int, int]:
    """Generate a random RGB tuple within a given channel range."""
    return (
        picker.randrange(low, high),
        picker.randrange(low, high),
        picker.randrange(low, high),
    )


def _apply_wave_distortion(image: Image.Image, picker: secrets.SystemRandom) -> Image.Image:
    """Apply sine-wave coordinate distortion to make OCR segmentation harder."""
    width, height = image.size
    amplitude_x = max(10, width // 36)
    amplitude_y = max(6, height // 28)
    frequency_x = picker.uniform(0.035, 0.085)
    frequency_y = picker.uniform(0.045, 0.095)
    phase_x = picker.uniform(0.0, math.tau)
    phase_y = picker.uniform(0.0, math.tau)

    source = image.load()
    warped = Image.new("RGB", (width, height), color=(246, 248, 252))
    target = warped.load()
    for y in range(height):
        horizontal_shift = int(amplitude_x * math.sin((y * frequency_x) + phase_x))
        for x in range(width):
            vertical_shift = int(amplitude_y * math.sin((x * frequency_y) + phase_y))
            src_x = x + horizontal_shift
            src_y = y + vertical_shift
            if 0 <= src_x < width and 0 <= src_y < height:
                target[x, y] = source[src_x, src_y]
            else:
                target[x, y] = _random_rgb(picker, 214, 245)

    return warped


def _render_captcha_data_url(captcha_text: str) -> str:
    """Execute render captcha data url."""
    width = max(520, int(current_app.config.get("CAPTCHA_IMAGE_WIDTH", 540)))
    height = max(160, int(current_app.config.get("CAPTCHA_IMAGE_HEIGHT", 180)))
    picker = secrets.SystemRandom()

    image = Image.new("RGB", (width, height), color=(245, 247, 252))
    draw = ImageDraw.Draw(image)

    # Gradient base so threshold-based OCR has no stable background.
    for y in range(height):
        base = max(196, min(252, 226 + int((y / max(1, height - 1)) * 18) + picker.randrange(-4, 5)))
        draw.line((0, y, width, y), fill=(base, min(255, base + 4), min(255, base + 8)), width=1)

    # Dense low-contrast background structure.
    for _ in range(max(18, width // 22)):
        x = picker.randrange(0, width)
        draw.line(
            (x, 0, min(width - 1, x + picker.randrange(-18, 19)), height - 1),
            fill=_random_rgb(picker, 170, 228),
            width=picker.randrange(1, 3),
        )
    for _ in range(max(12, height // 10)):
        y = picker.randrange(0, height)
        draw.line(
            (0, y, width - 1, min(height - 1, y + picker.randrange(-16, 17))),
            fill=_random_rgb(picker, 176, 234),
            width=picker.randrange(1, 3),
        )
    for _ in range(14):
        x0 = picker.randrange(-width // 3, width)
        y0 = picker.randrange(-height // 2, height)
        x1 = x0 + picker.randrange(width // 3, width)
        y1 = y0 + picker.randrange(height // 3, height)
        draw.arc(
            (x0, y0, x1, y1),
            start=picker.randrange(0, 360),
            end=picker.randrange(0, 360),
            fill=_random_rgb(picker, 150, 220),
            width=picker.randrange(1, 3),
        )

    for _ in range(max(200, (width * height) // 120)):
        draw.point(
            (picker.randrange(0, width), picker.randrange(0, height)),
            fill=_random_rgb(picker, 165, 236),
        )

    font_size = max(56, int(height * 0.56))
    font = _load_captcha_font(font_size)
    character_count = max(1, len(captcha_text))
    x_margin = max(34, width // 11)
    usable_width = max(width - (x_margin * 2), character_count * 94)
    slot_width = usable_width / character_count
    overlap = max(12, int(slot_width * 0.18))

    for char_index, char in enumerate(captcha_text):
        glyph_w = max(58, int(slot_width * 0.68))
        glyph_h = max(100, int(font_size * 1.18))
        glyph = Image.new("RGBA", (glyph_w, glyph_h), (0, 0, 0, 0))
        glyph_draw = ImageDraw.Draw(glyph)
        bbox = glyph_draw.textbbox((0, 0), char, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (glyph_w - text_w) // 2
        text_y = (glyph_h - text_h) // 2
        glyph_draw.text(
            (text_x, text_y),
            char,
            font=font,
            fill=(
                picker.randrange(14, 52),
                picker.randrange(14, 52),
                picker.randrange(14, 52),
                255,
            ),
            stroke_width=picker.randrange(1, 3),
            stroke_fill=(picker.randrange(70, 146), picker.randrange(70, 146), picker.randrange(70, 146), 210),
        )
        rotated = glyph.rotate(
            picker.randrange(-32, 33),
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )
        shear_x = picker.uniform(-0.35, 0.35)
        shear_y = picker.uniform(-0.20, 0.20)
        sheared = rotated.transform(
            rotated.size,
            Image.Transform.AFFINE,
            (1, shear_x, 0, shear_y, 1, 0),
            resample=Image.Resampling.BICUBIC,
        )
        base_x = int(x_margin + (char_index * slot_width) - (char_index * overlap))
        x = base_x + max(0, int((slot_width - sheared.width) / 2)) + picker.randrange(-8, 9)
        y = max(6, int((height - sheared.height) / 2) + picker.randrange(-18, 19))
        x = max(1, min(width - sheared.width - 1, x))
        y = max(1, min(height - sheared.height - 1, y))
        image.paste(sheared, (x, y), sheared)

    # Decoy glyphs to confuse OCR segmentation.
    for _ in range(max(6, character_count * 3)):
        decoy_char = picker.choice(CAPTCHA_ALPHABET)
        decoy_size = max(24, int(font_size * picker.uniform(0.40, 0.68)))
        decoy_font = _load_captcha_font(decoy_size)
        decoy = Image.new("RGBA", (decoy_size * 2, decoy_size * 2), (0, 0, 0, 0))
        decoy_draw = ImageDraw.Draw(decoy)
        decoy_draw.text(
            (picker.randrange(0, max(1, decoy_size // 2)), picker.randrange(0, max(1, decoy_size // 2))),
            decoy_char,
            font=decoy_font,
            fill=(picker.randrange(76, 160), picker.randrange(76, 160), picker.randrange(76, 160), 120),
            stroke_width=picker.randrange(0, 2),
        )
        decoy = decoy.rotate(picker.randrange(-50, 51), resample=Image.Resampling.BICUBIC, expand=True)
        image.paste(
            decoy,
            (
                picker.randrange(-20, max(1, width - decoy.width + 20)),
                picker.randrange(-20, max(1, height - decoy.height + 20)),
            ),
            decoy,
        )

    # Foreground occlusion lines over characters.
    for _ in range(11):
        draw.line(
            (
                picker.randrange(0, width // 4),
                picker.randrange(0, height),
                picker.randrange(width - (width // 4), width),
                picker.randrange(0, height),
            ),
            fill=_random_rgb(picker, 56, 174),
            width=picker.randrange(2, 4),
        )
    for _ in range(8):
        x0 = picker.randrange(-width // 4, width)
        y0 = picker.randrange(-height // 3, height)
        x1 = x0 + picker.randrange(width // 2, width)
        y1 = y0 + picker.randrange(height // 2, height)
        draw.arc(
            (x0, y0, x1, y1),
            start=picker.randrange(0, 360),
            end=picker.randrange(0, 360),
            fill=_random_rgb(picker, 48, 160),
            width=picker.randrange(2, 4),
        )

    image = _apply_wave_distortion(image, picker)
    image = image.filter(ImageFilter.GaussianBlur(radius=0.45))

    draw = ImageDraw.Draw(image)
    for _ in range(max(900, (width * height) // 75)):
        draw.point(
            (picker.randrange(0, width), picker.randrange(0, height)),
            fill=_random_rgb(picker, 25, 242),
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _validate_captcha(captcha_id: str | None, captcha_answer: str | None):
    """Execute validate captcha."""
    if not current_app.config.get("CAPTCHA_ENABLED"):
        return None

    challenge_id = (captcha_id or "").strip()
    answer = _normalize_captcha_text(captcha_answer or "")
    if not challenge_id or not answer:
        return error_response("captcha_required", "Captcha is required", status=400)

    db = get_db()
    now_epoch = int(time.time())
    prune_expired_captcha_challenges(db, now_epoch)
    challenge = get_captcha_challenge(db, challenge_id)
    if not challenge:
        return error_response("captcha_invalid", "Captcha is invalid or expired", status=400)

    delete_captcha_challenge(db, challenge_id)
    if now_epoch > int(challenge["expires_at"]):
        return error_response("captcha_expired", "Captcha expired", status=400)

    if _is_dev_bypass_code(answer, config_flag="CAPTCHA_DEV_MODE"):
        return None

    if not secrets.compare_digest(challenge["answer_hash"], _hash_secret(answer)):
        return error_response("captcha_invalid", "Captcha answer is incorrect", status=400)
    return None


def _issue_token(user: dict):
    """Execute issue token."""
    update_last_login(get_db(), user["id"])
    token = create_token(user["id"], user["username"], user["role"])
    log_event(logger, "login_success", username=user["username"], request_id=g.get("request_id"))
    return ok_response({"token": token, "user": _format_user_payload(user)})


def _generate_otp_code(length: int) -> str:
    """Execute generate otp code."""
    size = max(4, min(length, 12))
    return "".join(str(secrets.randbelow(10)) for _ in range(size))


def _send_or_fallback_otp(session_id: str, email: str, otp_code: str, status: int = 200):
    """Execute send or fallback otp."""
    ok, err = send_otp_email(email, otp_code)
    payload = {
        "otp_required": True,
        "otp_session": session_id,
        "delivery": "email",
        "email": _mask_email(email),
    }

    if ok:
        return ok_response(payload, status=status)

    if current_app.config.get("OTP_DEV_MODE"):
        payload["delivery"] = "development"
        payload["dev_otp"] = otp_code
        payload["warning"] = err or "SMTP is not configured"
        return ok_response(payload, status=status)

    delete_otp_session(get_db(), session_id)
    return error_response("otp_delivery_failed", "Unable to deliver OTP code", details=err, status=503)


def _start_otp_challenge(user: dict, purpose: str, status: int = 200):
    """Execute start otp challenge."""
    if not current_app.config.get("OTP_ENABLED"):
        return None

    email = (user.get("email") or "").strip()
    if not email:
        # Keep legacy/no-email users (for example seeded admin accounts) able to authenticate.
        log_event(
            logger,
            "otp_skipped_missing_email",
            user_id=user.get("id"),
            username=user.get("username"),
            request_id=g.get("request_id"),
        )
        return _issue_token(user)

    db = get_db()
    now_epoch = int(time.time())
    prune_expired_otp_sessions(db, now_epoch)

    otp_code = _generate_otp_code(current_app.config["OTP_LENGTH"])
    session_id = uuid.uuid4().hex
    expires_at = now_epoch + max(60, int(current_app.config["OTP_TTL_SEC"]))
    create_otp_session(
        db,
        session_id=session_id,
        user_id=int(user["id"]),
        purpose=purpose,
        email=email,
        otp_hash=_hash_secret(otp_code),
        max_attempts=max(1, int(current_app.config["OTP_MAX_ATTEMPTS"])),
        created_at=now_epoch,
        expires_at=expires_at,
    )
    return _send_or_fallback_otp(session_id, email, otp_code, status=status)


@auth_bp.get("/captcha")
def captcha():
    """Return a captcha challenge for auth requests."""
    if not current_app.config.get("CAPTCHA_ENABLED"):
        return ok_response({"enabled": False})

    answer = _generate_captcha_code(current_app.config.get("CAPTCHA_LENGTH", 5))
    image_base64 = _render_captcha_data_url(answer)
    challenge_id = uuid.uuid4().hex
    now_epoch = int(time.time())
    ttl = max(60, int(current_app.config["CAPTCHA_TTL_SEC"]))

    db = get_db()
    prune_expired_captcha_challenges(db, now_epoch)
    create_captcha_challenge(
        db,
        captcha_id=challenge_id,
        answer_hash=_hash_secret(answer),
        created_at=now_epoch,
        expires_at=now_epoch + ttl,
    )
    payload = {
        "enabled": True,
        "captcha_id": challenge_id,
        "captcha_type": "image",
        "image_base64": image_base64,
        "prompt": "Type the 5-digit code shown in the image.",
        "expires_in": ttl,
    }
    if current_app.config.get("TESTING") or current_app.config.get("CAPTCHA_DEV_MODE"):
        payload["captcha_text"] = answer
    return ok_response(payload)


@auth_bp.post("/login")
def login():
    """Authenticate a user and return a JWT or OTP challenge."""
    payload = request.get_json(silent=True) or {}
    form = LoginForm(formdata=_json_to_form_data(payload))
    if not form.validate():
        return error_response("validation_error", "Invalid login payload", details=form.errors)
    try:
        data = LoginRequest(**payload)
    except ValidationError as exc:
        return error_response("validation_error", "Invalid login payload", details=_safe_validation_errors(exc))

    captcha_error = _validate_captcha(data.captcha_id, data.captcha_answer)
    if captcha_error:
        return captcha_error

    limiter = _get_limiter()
    normalized_email = _normalize_email(data.email)
    identifier = data.username or normalized_email or "unknown"
    key = f"{request.remote_addr}:{identifier}"
    if limiter.is_blocked(key):
        return error_response("rate_limited", "Too many login attempts", status=429)

    db = get_db()
    user = get_user_by_username(db, data.username) if data.username else get_user_by_email(db, normalized_email)
    if not user or not verify_password(data.password, user["password_hash"]):
        limiter.record_failure(key)
        return error_response("invalid_credentials", "Invalid username or password", status=401)

    limiter.reset(key)
    if current_app.config.get("OTP_ENABLED"):
        return _start_otp_challenge(user, purpose="login")

    return _issue_token(user)


def _register_account():
    """Execute register account."""
    payload = request.get_json(silent=True) or {}
    form = RegisterForm(formdata=_json_to_form_data(payload))
    if not form.validate():
        return error_response("validation_error", "Invalid registration payload", details=form.errors)
    try:
        data = RegisterRequest(**payload)
    except ValidationError as exc:
        return error_response("validation_error", "Invalid registration payload", details=_safe_validation_errors(exc))

    captcha_error = _validate_captcha(data.captcha_id, data.captcha_answer)
    if captcha_error:
        return captcha_error

    normalized_email = _normalize_email(data.email)

    if current_app.config.get("OTP_ENABLED") and not normalized_email:
        return error_response("validation_error", "Email is required when OTP is enabled", status=400)

    db = get_db()
    if normalized_email and get_user_by_email(db, normalized_email):
        return error_response("conflict", "Email already exists", status=409)

    username = (data.username or "").strip()
    if not username and normalized_email:
        username = _username_from_email(normalized_email)
    if not username:
        return error_response("validation_error", "Username is required", status=400)

    existing = get_user_by_username(db, username)
    if existing and data.username:
        return error_response("conflict", "Username already exists", status=409)
    if existing and not data.username:
        suffix = 1
        candidate = f"{username}{suffix}"
        while get_user_by_username(db, candidate):
            suffix += 1
            candidate = f"{username}{suffix}"
        username = candidate

    display_name = (data.name or username).strip()[:120]
    avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={normalized_email or username}"
    try:
        user_id = create_user(
            db,
            username,
            hash_password(data.password),
            role="user",
            email=normalized_email,
            display_name=display_name,
            avatar=avatar,
        )
    except sqlite3.IntegrityError as exc:
        db.rollback()
        details = str(exc).lower()
        if "username" in details:
            return error_response("conflict", "Username already exists", status=409)
        if "email" in details:
            return error_response("conflict", "Email already exists", status=409)
        return error_response("conflict", "User already exists", status=409)
    user = get_user_by_id(db, user_id)
    if current_app.config.get("OTP_ENABLED"):
        return _start_otp_challenge(user, purpose="signup", status=201)

    token = create_token(user_id, username, "user")
    return ok_response({"token": token, "user": _format_user_payload(user)}, status=201)


@auth_bp.post("/register")
def register():
    """Register a new user account."""
    return _register_account()


@auth_bp.post("/signup")
def signup():
    """Alias for clients that call signup instead of register."""
    return _register_account()


@auth_bp.post("/otp/verify")
def otp_verify():
    """Verify one-time-password and complete login/signup."""
    if not current_app.config.get("OTP_ENABLED"):
        return error_response("otp_disabled", "OTP verification is disabled", status=400)

    payload = request.get_json(silent=True) or {}
    try:
        data = OtpVerifyRequest(**payload)
    except ValidationError as exc:
        return error_response("validation_error", "Invalid OTP payload", details=_safe_validation_errors(exc))

    db = get_db()
    now_epoch = int(time.time())
    prune_expired_otp_sessions(db, now_epoch)
    session = get_otp_session(db, data.otp_session)
    if not session:
        return error_response("invalid_otp_session", "OTP session not found", status=400)
    if session.get("consumed_at"):
        return error_response("otp_used", "OTP session already used", status=400)
    if now_epoch > int(session["expires_at"]):
        delete_otp_session(db, data.otp_session)
        return error_response("otp_expired", "OTP expired", status=401)

    submitted_code = data.otp_code.strip()
    submitted_hash = _hash_secret(submitted_code)
    if not _is_dev_bypass_code(submitted_code, config_flag="OTP_DEV_MODE") and not secrets.compare_digest(
        session["otp_hash"], submitted_hash
    ):
        attempts = int(session.get("attempts", 0)) + 1
        if attempts >= int(session.get("max_attempts", current_app.config["OTP_MAX_ATTEMPTS"])):
            delete_otp_session(db, data.otp_session)
            return error_response("otp_locked", "Too many invalid OTP attempts", status=401)
        update_otp_session_attempts(db, data.otp_session, attempts)
        return error_response("invalid_otp", "Invalid OTP code", status=401)

    consume_otp_session(db, data.otp_session, now_epoch)
    user = get_user_by_id(db, int(session["user_id"]))
    if not user:
        return error_response("not_found", "User not found", status=404)
    delete_otp_session(db, data.otp_session)
    return _issue_token(user)


@auth_bp.post("/otp/resend")
def otp_resend():
    """Resend OTP for an active OTP session."""
    if not current_app.config.get("OTP_ENABLED"):
        return error_response("otp_disabled", "OTP verification is disabled", status=400)

    payload = request.get_json(silent=True) or {}
    try:
        data = OtpResendRequest(**payload)
    except ValidationError as exc:
        return error_response("validation_error", "Invalid OTP resend payload", details=_safe_validation_errors(exc))

    db = get_db()
    now_epoch = int(time.time())
    prune_expired_otp_sessions(db, now_epoch)
    session = get_otp_session(db, data.otp_session)
    if not session:
        return error_response("invalid_otp_session", "OTP session not found", status=400)
    if session.get("consumed_at"):
        return error_response("otp_used", "OTP session already used", status=400)

    otp_code = _generate_otp_code(current_app.config["OTP_LENGTH"])
    expires_at = now_epoch + max(60, int(current_app.config["OTP_TTL_SEC"]))
    update_otp_session_code(db, data.otp_session, _hash_secret(otp_code), expires_at)
    return _send_or_fallback_otp(data.otp_session, session["email"], otp_code)


def _build_password_reset_link(reset_token: str, reset_code: str) -> str:
    """Build an absolute one-time reset URL that opens the Jinja auth page."""
    auth_page_url = url_for("views.auth_page", _external=True)
    return f"{auth_page_url}?reset_token={quote(reset_token, safe='')}&reset_code={quote(reset_code, safe='')}"


@auth_bp.post("/password/forgot")
def forgot_password():
    """Issue a one-time password reset link and deliver it over SMTP."""
    payload = request.get_json(silent=True) or {}
    try:
        data = PasswordForgotRequest(**payload)
    except ValidationError as exc:
        return error_response(
            "validation_error", "Invalid forgot-password payload", details=_safe_validation_errors(exc)
        )

    email = _normalize_email(data.email)
    if not email or "@" not in email:
        return error_response("validation_error", "Email is invalid", status=400)

    db = get_db()
    user = get_user_by_email(db, email)
    # Avoid user enumeration by returning a successful response even for unknown emails.
    generic_message = "If that email exists, a one-time reset link has been sent."
    if not user:
        return ok_response({"requested": True, "message": generic_message})

    now_epoch = int(time.time())
    prune_expired_otp_sessions(db, now_epoch)
    db.execute(
        "DELETE FROM otp_sessions WHERE user_id = ? AND purpose = ?",
        (int(user["id"]), "password_reset"),
    )
    db.commit()

    reset_token = uuid.uuid4().hex
    reset_code = secrets.token_urlsafe(32)
    reset_ttl = max(300, int(current_app.config.get("PASSWORD_RESET_TTL_SEC", 1800)))

    create_otp_session(
        db,
        session_id=reset_token,
        user_id=int(user["id"]),
        purpose="password_reset",
        email=str(user.get("email") or email),
        otp_hash=_hash_secret(reset_code),
        max_attempts=2,
        created_at=now_epoch,
        expires_at=now_epoch + reset_ttl,
    )

    reset_link = _build_password_reset_link(reset_token, reset_code)
    ok, err = send_password_reset_email(str(user.get("email") or email), reset_link, reset_ttl)
    if ok:
        return ok_response(
            {
                "requested": True,
                "message": "Password reset link sent to your email.",
                "delivery": "email",
                "email": _mask_email(str(user.get("email") or email)),
            }
        )

    if current_app.config.get("TESTING") or current_app.config.get("OTP_DEV_MODE"):
        return ok_response(
            {
                "requested": True,
                "message": "Password reset link generated in development mode.",
                "delivery": "development",
                "email": _mask_email(str(user.get("email") or email)),
                "warning": err or "SMTP is not configured",
                "reset_link": reset_link,
            }
        )

    delete_otp_session(db, reset_token)
    return error_response(
        "password_reset_delivery_failed",
        "Unable to deliver password reset link",
        details=err,
        status=503,
    )


@auth_bp.post("/password/reset")
def reset_password():
    """Consume a one-time reset link and rotate the user's password."""
    payload = request.get_json(silent=True) or {}
    try:
        data = PasswordResetRequest(**payload)
    except ValidationError as exc:
        return error_response(
            "validation_error", "Invalid password reset payload", details=_safe_validation_errors(exc)
        )

    reset_token = data.reset_token.strip()
    reset_code = data.reset_code.strip()

    db = get_db()
    now_epoch = int(time.time())
    prune_expired_otp_sessions(db, now_epoch)
    session = get_otp_session(db, reset_token)
    if not session or str(session.get("purpose") or "") != "password_reset":
        return error_response("invalid_reset_link", "Password reset link is invalid or expired", status=400)

    if session.get("consumed_at"):
        delete_otp_session(db, reset_token)
        return error_response("invalid_reset_link", "Password reset link is invalid or expired", status=400)

    if now_epoch > int(session["expires_at"]):
        delete_otp_session(db, reset_token)
        return error_response("reset_link_expired", "Password reset link expired", status=401)

    submitted_hash = _hash_secret(reset_code)
    if not secrets.compare_digest(str(session["otp_hash"]), submitted_hash):
        attempts = int(session.get("attempts", 0)) + 1
        if attempts >= int(session.get("max_attempts", 2)):
            delete_otp_session(db, reset_token)
            return error_response("invalid_reset_link", "Password reset link is invalid or expired", status=400)
        update_otp_session_attempts(db, reset_token, attempts)
        return error_response("invalid_reset_link", "Password reset link is invalid or expired", status=400)

    user = get_user_by_id(db, int(session["user_id"]))
    if not user:
        delete_otp_session(db, reset_token)
        return error_response("not_found", "User not found", status=404)

    if verify_password(data.new_password, user["password_hash"]):
        return error_response("validation_error", "New password must be different", status=400)

    consume_otp_session(db, reset_token, now_epoch)
    update_user_password_hash(db, int(user["id"]), hash_password(data.new_password))
    delete_otp_session(db, reset_token)
    log_event(logger, "password_reset_success", user_id=int(user["id"]), request_id=g.get("request_id"))
    return ok_response({"reset": True})


@auth_bp.post("/logout")
@jwt_required
def logout():
    """Invalidate the client session (stateless JWT)."""
    return ok_response({"message": "Logged out"})


@auth_bp.patch("/profile")
@jwt_required
def update_profile():
    """Update profile fields for the current user."""
    payload = request.get_json(silent=True) or {}
    try:
        data = ProfileUpdateRequest(**payload)
    except ValidationError as exc:
        return error_response("validation_error", "Invalid profile payload", details=_safe_validation_errors(exc))

    user_id = int(g.user["sub"])
    db = get_db()
    user = get_user_by_id(db, user_id)
    if not user:
        return error_response("not_found", "User not found", status=404)

    display_name = data.name.strip() if data.name is not None else None
    email = _normalize_email(data.email) if data.email is not None else None
    avatar = data.avatar.strip() if data.avatar is not None else None

    if email is not None:
        if "@" not in email:
            return error_response("validation_error", "Email is invalid", status=400)
        existing = get_user_by_email(db, email)
        if existing and int(existing["id"]) != user_id:
            return error_response("conflict", "Email already exists", status=409)

    if display_name is None and email is None and avatar is None:
        return error_response("validation_error", "No profile fields were provided", status=400)

    update_user_profile(db, user_id, display_name=display_name, email=email, avatar=avatar)
    updated = get_user_by_id(db, user_id)
    return ok_response({"user": _format_user_payload(updated)})


@auth_bp.delete("/profile")
@jwt_required
def delete_profile():
    """Delete the authenticated user profile after explicit confirmation."""
    payload = request.get_json(silent=True) or {}
    confirm = str(payload.get("confirm") or "").strip().upper()
    if confirm != "DELETE":
        return error_response(
            "validation_error",
            "Profile deletion requires confirm='DELETE'. This action is permanent.",
            status=400,
        )

    user_id = int(g.user["sub"])
    db = get_db()
    user = get_user_by_id(db, user_id)
    if not user:
        return error_response("not_found", "User not found", status=404)

    _delete_avatar_file_if_local(user.get("avatar"))
    removed = delete_user_by_id(db, user_id)
    if not removed:
        return error_response("not_found", "User not found", status=404)
    return ok_response({"deleted": True})


@auth_bp.post("/password")
@jwt_required
def change_password():
    """Change password for the current user after verifying current password."""
    payload = request.get_json(silent=True) or {}
    try:
        data = PasswordChangeRequest(**payload)
    except ValidationError as exc:
        return error_response("validation_error", "Invalid password payload", details=_safe_validation_errors(exc))

    user_id = int(g.user["sub"])
    db = get_db()
    user = get_user_by_id(db, user_id)
    if not user:
        return error_response("not_found", "User not found", status=404)

    if not verify_password(data.current_password, user["password_hash"]):
        return error_response("invalid_credentials", "Current password is incorrect", status=401)
    if data.current_password == data.new_password:
        return error_response("validation_error", "New password must be different", status=400)

    update_user_password_hash(db, user_id, hash_password(data.new_password))
    return ok_response({"changed": True})


@auth_bp.post("/avatar")
@jwt_required
def upload_avatar():
    """Upload and set profile avatar for the current user."""
    file_storage = request.files.get("image")
    try:
        image_bytes, ext, _ = read_image_bytes(file_storage)
    except ValueError as exc:
        return error_response("invalid_image", "Invalid image upload", details=str(exc), status=400)

    user_id = int(g.user["sub"])
    avatars_dir = Path(current_app.config["UPLOAD_DIR"]).expanduser().resolve() / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    filename = f"avatar_u{user_id}_{uuid.uuid4().hex}.{ext}"
    file_path = avatars_dir / filename
    file_path.write_bytes(image_bytes)

    avatar_path = f"/api/auth/avatar/{filename}"
    update_user_profile(get_db(), user_id, avatar=avatar_path)
    user = get_user_by_id(get_db(), user_id)
    return ok_response({"user": _format_user_payload(user)})


@auth_bp.get("/avatar/<string:filename>")
@jwt_required(allow_query_token=True)
def get_avatar(filename: str):
    """Serve avatar image if requester is owner/admin."""
    if "/" in filename or "\\" in filename or ".." in filename:
        return error_response("not_found", "Avatar not found", status=404)

    match = re.match(r"^avatar_u(\d+)_", filename)
    if not match:
        return error_response("not_found", "Avatar not found", status=404)

    owner_id = int(match.group(1))
    requester_id = int(g.user["sub"])
    requester_role = str(g.user.get("role") or "")
    if requester_id != owner_id and requester_role != "admin":
        return error_response("not_found", "Avatar not found", status=404)

    avatars_dir = Path(current_app.config["UPLOAD_DIR"]).expanduser().resolve() / "avatars"
    file_path = resolve_uploaded_file_path(avatars_dir, filename)
    if not file_path:
        return error_response("not_found", "Avatar not found", status=404)
    try:
        return send_file(file_path, mimetype=_resolve_image_mimetype(file_path))
    except FileNotFoundError:
        return error_response("not_found", "Avatar not found", status=404)
    except OSError:
        return error_response("not_found", "Avatar not found", status=404)


@auth_bp.get("/me")
@jwt_required
def me():
    """Return the current authenticated user."""
    db = get_db()
    user = get_user_by_id(db, g.user["sub"])
    if not user:
        return error_response("not_found", "User not found", status=404)
    return ok_response({"user": _format_user_payload(user)})
