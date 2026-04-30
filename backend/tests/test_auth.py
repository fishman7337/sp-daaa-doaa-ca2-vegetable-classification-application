"""Authentication API tests for login, signup, profile, and OTP flows."""

from __future__ import annotations

import base64
import io
from urllib.parse import parse_qs, urlparse

import pytest
from PIL import Image

from backend.db import get_db
from backend.repository import get_user_by_username
from backend.utils.security import hash_password, seed_admin, verify_password

from .conftest import make_image_bytes

pytestmark = [pytest.mark.api]


def test_login_success(client):
    """Return a JWT for valid admin credentials."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["data"]["token"]


@pytest.mark.expected_failure
def test_login_invalid(client):
    """Reject invalid credentials."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.expected_failure
def test_me_requires_auth(client):
    """Require bearer token for `/api/auth/me`."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_logout(client):
    """Allow authenticated clients to call logout."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = resp.get_json()["data"]["token"]
    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_me_success(client):
    """Return authenticated user profile data."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = resp.get_json()["data"]["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.validity
def test_register_success(client):
    """Create a user account through `/api/auth/register`."""
    resp = client.post("/api/auth/register", json={"username": "newuser", "password": "pass1234", "agree_terms": True})
    assert resp.status_code == 201
    payload = resp.get_json()["data"]
    assert payload["token"]


@pytest.mark.expected_failure
def test_register_duplicate(client):
    """Reject duplicate usernames."""
    resp = client.post("/api/auth/register", json={"username": "dupe", "password": "pass1234", "agree_terms": True})
    assert resp.status_code == 201
    resp = client.post("/api/auth/register", json={"username": "dupe", "password": "pass1234", "agree_terms": True})
    assert resp.status_code == 409


def test_signup_with_email_and_name(client):
    """Create a user account with email and display name."""
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Veggie User", "email": "veggie@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert resp.status_code == 201
    payload = resp.get_json()["data"]
    assert payload["token"]
    assert payload["user"]["email"] == "veggie@example.com"
    assert payload["user"]["name"] == "Veggie User"


def test_signup_without_terms_field_is_rejected(client):
    """Reject signup when terms agreement is missing."""
    resp = client.post(
        "/api/auth/signup",
        json={"name": "No Terms", "email": "noterms@example.com", "password": "pass1234"},
    )
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["error"]["code"] == "validation_error"


def test_signup_rejects_duplicate_email_case_insensitive(client):
    """Reject duplicate email registrations regardless of letter case."""
    first = client.post(
        "/api/auth/signup",
        json={"name": "Case One", "email": "CaseDup@Example.com", "password": "pass1234", "agree_terms": True},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/auth/signup",
        json={"name": "Case Two", "email": "casedup@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "conflict"


def test_captcha_image_respects_configured_dimensions(client):
    """Render captcha at configured dimensions for legibility controls."""
    client.application.config["CAPTCHA_ENABLED"] = True
    client.application.config["CAPTCHA_DEV_MODE"] = True
    client.application.config["CAPTCHA_IMAGE_WIDTH"] = 520
    client.application.config["CAPTCHA_IMAGE_HEIGHT"] = 170

    response = client.get("/api/auth/captcha")
    assert response.status_code == 200
    payload = response.get_json()["data"]
    encoded = payload["image_base64"].split(",", maxsplit=1)[1]
    raw = base64.b64decode(encoded)
    image = Image.open(io.BytesIO(raw))
    assert image.size == (520, 170)


def test_captcha_respects_configured_length(client):
    """Render captcha text at configured challenge length."""
    client.application.config["CAPTCHA_ENABLED"] = True
    client.application.config["CAPTCHA_DEV_MODE"] = True
    client.application.config["CAPTCHA_LENGTH"] = 5

    response = client.get("/api/auth/captcha")
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert len(str(payload["captcha_text"])) == 5


def test_login_with_email(client):
    """Allow login using email/password."""
    register = client.post(
        "/api/auth/signup",
        json={"name": "Email User", "email": "emailuser@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"email": "emailuser@example.com", "password": "pass1234"},
    )
    assert login.status_code == 200
    payload = login.get_json()["data"]
    assert payload["user"]["email"] == "emailuser@example.com"


@pytest.mark.consistency
def test_password_hashing_uses_salt():
    """Generate different salted hashes for the same plaintext password."""
    password = "pass1234"
    first = hash_password(password)
    second = hash_password(password)

    assert first != password
    assert second != password
    assert first != second
    assert verify_password(password, first)
    assert verify_password(password, second)


def test_password_verification_rejects_invalid_hash_format():
    """Treat malformed stored password hashes as failed verification."""
    assert verify_password("pass1234", "not-a-bcrypt-hash") is False


def test_seed_admin_is_idempotent(app):
    """Avoid creating duplicate admin users when setup runs more than once."""
    with app.app_context():
        db = get_db()
        before = get_user_by_username(db, "admin")
        assert before is not None

        seed_admin(db, "admin", "replacement-password")

        after = get_user_by_username(db, "admin")
        assert after["id"] == before["id"]
        assert after["password_hash"] == before["password_hash"]


def test_login_requires_captcha_when_enabled(client):
    """Enforce captcha challenge when captcha is enabled."""
    client.application.config["CAPTCHA_ENABLED"] = True
    client.application.config["CAPTCHA_DEV_MODE"] = True
    client.application.config["OTP_ENABLED"] = False

    missing = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert missing.status_code == 400

    captcha = client.get("/api/auth/captcha")
    assert captcha.status_code == 200
    payload = captcha.get_json()["data"]
    assert payload["enabled"] is True
    assert payload["captcha_type"] == "image"
    assert payload["image_base64"].startswith("data:image/png;base64,")
    answer = payload["captcha_text"]

    login = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123",
            "captcha_id": payload["captcha_id"],
            "captcha_answer": answer,
        },
    )
    assert login.status_code == 200
    assert login.get_json()["data"]["token"]


def test_login_accepts_dev_captcha_bypass_code(client):
    """Accept fixed captcha bypass code only when captcha dev mode is enabled."""
    client.application.config["CAPTCHA_ENABLED"] = True
    client.application.config["CAPTCHA_DEV_MODE"] = True
    client.application.config["OTP_ENABLED"] = False

    captcha = client.get("/api/auth/captcha")
    assert captcha.status_code == 200
    payload = captcha.get_json()["data"]

    login = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123",
            "captcha_id": payload["captcha_id"],
            "captcha_answer": "00000",
        },
    )
    assert login.status_code == 200
    assert login.get_json()["data"]["token"]


def test_login_rejects_dev_captcha_bypass_code_when_disabled(client):
    """Reject fixed captcha bypass code outside captcha dev mode."""
    client.application.config["CAPTCHA_ENABLED"] = True
    client.application.config["CAPTCHA_DEV_MODE"] = False
    client.application.config["OTP_ENABLED"] = False

    captcha = client.get("/api/auth/captcha")
    assert captcha.status_code == 200
    payload = captcha.get_json()["data"]
    for _ in range(5):
        if payload.get("captcha_text") != "00000":
            break
        captcha = client.get("/api/auth/captcha")
        assert captcha.status_code == 200
        payload = captcha.get_json()["data"]
    assert payload.get("captcha_text") != "00000"

    login = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123",
            "captcha_id": payload["captcha_id"],
            "captcha_answer": "00000",
        },
    )
    assert login.status_code == 400
    assert login.get_json()["error"]["code"] == "captcha_invalid"


def test_signup_otp_flow_in_dev_mode(client):
    """Validate OTP signup flow in development mode."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = True
    client.application.config["OTP_DEV_MODE"] = True

    signup = client.post(
        "/api/auth/signup",
        json={"name": "Otp User", "email": "otp-user@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201
    signup_payload = signup.get_json()["data"]
    assert signup_payload["otp_required"] is True
    assert signup_payload["otp_session"]
    assert signup_payload["dev_otp"]

    wrong = client.post(
        "/api/auth/otp/verify",
        json={"otp_session": signup_payload["otp_session"], "otp_code": "000000"},
    )
    assert wrong.status_code == 401

    verify = client.post(
        "/api/auth/otp/verify",
        json={"otp_session": signup_payload["otp_session"], "otp_code": signup_payload["dev_otp"]},
    )
    assert verify.status_code == 200
    verify_payload = verify.get_json()["data"]
    assert verify_payload["token"]
    assert verify_payload["user"]["email"] == "otp-user@example.com"


def test_signup_accepts_dev_otp_bypass_code(client):
    """Accept fixed OTP bypass code only when OTP dev mode is enabled."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = True
    client.application.config["OTP_DEV_MODE"] = True

    signup = client.post(
        "/api/auth/signup",
        json={"name": "Otp Bypass", "email": "otp-bypass@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201
    signup_payload = signup.get_json()["data"]
    assert signup_payload["otp_required"] is True
    assert signup_payload["otp_session"]

    verify = client.post(
        "/api/auth/otp/verify",
        json={"otp_session": signup_payload["otp_session"], "otp_code": "00000"},
    )
    assert verify.status_code == 200
    assert verify.get_json()["data"]["token"]


def test_signup_rejects_dev_otp_bypass_code_when_disabled(client, monkeypatch):
    """Reject fixed OTP bypass code outside OTP dev mode."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = True
    client.application.config["OTP_DEV_MODE"] = False

    def _mock_send_otp(_to_email: str, _otp_code: str):
        return True, None

    monkeypatch.setattr("backend.auth.send_otp_email", _mock_send_otp)

    signup = client.post(
        "/api/auth/signup",
        json={
            "name": "Otp No Bypass",
            "email": "otp-no-bypass@example.com",
            "password": "pass1234",
            "agree_terms": True,
        },
    )
    assert signup.status_code == 201
    signup_payload = signup.get_json()["data"]
    assert signup_payload["otp_required"] is True
    assert signup_payload["otp_session"]
    assert "dev_otp" not in signup_payload

    verify = client.post(
        "/api/auth/otp/verify",
        json={"otp_session": signup_payload["otp_session"], "otp_code": "00000"},
    )
    assert verify.status_code == 401
    assert verify.get_json()["error"]["code"] == "invalid_otp"


def test_login_otp_resend_flow(client):
    """Support OTP resend and subsequent verification."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = False
    create = client.post(
        "/api/auth/signup",
        json={"name": "Resend User", "email": "resend@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert create.status_code == 201

    client.application.config["OTP_ENABLED"] = True
    client.application.config["OTP_DEV_MODE"] = True

    login = client.post("/api/auth/login", json={"email": "resend@example.com", "password": "pass1234"})
    assert login.status_code == 200
    payload = login.get_json()["data"]
    assert payload["otp_required"] is True
    assert payload["dev_otp"]

    resend = client.post("/api/auth/otp/resend", json={"otp_session": payload["otp_session"]})
    assert resend.status_code == 200
    resend_payload = resend.get_json()["data"]
    assert resend_payload["otp_required"] is True
    assert resend_payload["dev_otp"]

    verify = client.post(
        "/api/auth/otp/verify",
        json={"otp_session": payload["otp_session"], "otp_code": resend_payload["dev_otp"]},
    )
    assert verify.status_code == 200
    assert verify.get_json()["data"]["token"]


def test_login_legacy_no_email_account_still_works_with_otp_enabled(client):
    """Allow seeded admin login when OTP is enabled but account has no email."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = True
    client.application.config["OTP_DEV_MODE"] = True

    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    payload = login.get_json()["data"]
    assert payload["token"]
    assert payload["user"]["username"] == "admin"
    assert "otp_required" not in payload


def test_forgot_password_unknown_email_returns_generic_success(client):
    """Return generic success response for unknown email addresses."""
    response = client.post("/api/auth/password/forgot", json={"email": "missing@example.com"})
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["requested"] is True
    assert "one-time reset link" in payload["message"].lower()


def test_forgot_password_returns_dev_link_when_smtp_unavailable(client, monkeypatch):
    """Return a development reset link when SMTP is unavailable in dev mode."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = False
    client.application.config["OTP_DEV_MODE"] = True

    signup = client.post(
        "/api/auth/signup",
        json={"name": "Recover User", "email": "recover-dev@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201

    def _mock_send(_to_email: str, _reset_link: str, _ttl_sec: int):
        return False, "smtp offline"

    monkeypatch.setattr("backend.auth.send_password_reset_email", _mock_send)
    forgot = client.post("/api/auth/password/forgot", json={"email": "recover-dev@example.com"})
    assert forgot.status_code == 200
    payload = forgot.get_json()["data"]
    assert payload["delivery"] == "development"
    assert payload["reset_link"]


def test_password_reset_link_flow_updates_credentials(client, monkeypatch):
    """Issue reset link, reset password once, and allow login with new password."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = False

    signup = client.post(
        "/api/auth/signup",
        json={"name": "Recover User", "email": "recover@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201

    sent: dict[str, str | int] = {}

    def _mock_send(to_email: str, reset_link: str, ttl_sec: int):
        sent["email"] = to_email
        sent["link"] = reset_link
        sent["ttl"] = ttl_sec
        return True, None

    monkeypatch.setattr("backend.auth.send_password_reset_email", _mock_send)
    forgot = client.post("/api/auth/password/forgot", json={"email": "recover@example.com"})
    assert forgot.status_code == 200
    assert sent["email"] == "recover@example.com"

    link = str(sent["link"])
    parsed = urlparse(link)
    params = parse_qs(parsed.query)
    reset_token = params["reset_token"][0]
    reset_code = params["reset_code"][0]

    reset = client.post(
        "/api/auth/password/reset",
        json={"reset_token": reset_token, "reset_code": reset_code, "new_password": "newpass123"},
    )
    assert reset.status_code == 200
    assert reset.get_json()["data"]["reset"] is True

    old_login = client.post("/api/auth/login", json={"email": "recover@example.com", "password": "pass1234"})
    assert old_login.status_code == 401
    new_login = client.post("/api/auth/login", json={"email": "recover@example.com", "password": "newpass123"})
    assert new_login.status_code == 200


def test_password_reset_link_is_one_time_use(client, monkeypatch):
    """Reject replay of a previously consumed password reset link."""
    client.application.config["CAPTCHA_ENABLED"] = False
    client.application.config["OTP_ENABLED"] = False

    signup = client.post(
        "/api/auth/signup",
        json={"name": "Replay User", "email": "replay@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201

    sent: dict[str, str] = {}

    def _mock_send(_to_email: str, reset_link: str, _ttl_sec: int):
        sent["link"] = reset_link
        return True, None

    monkeypatch.setattr("backend.auth.send_password_reset_email", _mock_send)
    forgot = client.post("/api/auth/password/forgot", json={"email": "replay@example.com"})
    assert forgot.status_code == 200

    parsed = urlparse(sent["link"])
    params = parse_qs(parsed.query)
    reset_token = params["reset_token"][0]
    reset_code = params["reset_code"][0]

    first = client.post(
        "/api/auth/password/reset",
        json={"reset_token": reset_token, "reset_code": reset_code, "new_password": "newpass123"},
    )
    assert first.status_code == 200

    replay = client.post(
        "/api/auth/password/reset",
        json={"reset_token": reset_token, "reset_code": reset_code, "new_password": "anotherpass123"},
    )
    assert replay.status_code == 400
    assert replay.get_json()["error"]["code"] == "invalid_reset_link"


def test_profile_update_and_password_change(client):
    """Update profile and rotate password via authenticated APIs."""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.patch(
        "/api/auth/profile",
        headers=headers,
        json={
            "name": "Admin Prime",
            "email": "admin.prime@example.com",
            "avatar": "https://example.com/avatar.png",
        },
    )
    assert profile.status_code == 200
    profile_user = profile.get_json()["data"]["user"]
    assert profile_user["name"] == "Admin Prime"
    assert profile_user["email"] == "admin.prime@example.com"
    assert profile_user["avatar"] == "https://example.com/avatar.png"

    wrong = client.post(
        "/api/auth/password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "newpass123"},
    )
    assert wrong.status_code == 401

    changed = client.post(
        "/api/auth/password",
        headers=headers,
        json={"current_password": "admin123", "new_password": "newpass123"},
    )
    assert changed.status_code == 200
    assert changed.get_json()["data"]["changed"] is True

    old_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert old_login.status_code == 401
    new_login = client.post("/api/auth/login", json={"username": "admin", "password": "newpass123"})
    assert new_login.status_code == 200


def test_profile_delete_requires_explicit_confirmation(client):
    """Reject profile deletion unless confirm='DELETE' is provided."""
    signup = client.post(
        "/api/auth/signup",
        json={"name": "Delete Guard", "email": "delete-guard@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201

    login = client.post("/api/auth/login", json={"email": "delete-guard@example.com", "password": "pass1234"})
    assert login.status_code == 200
    token = login.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    missing_confirm = client.delete("/api/auth/profile", headers=headers, json={})
    assert missing_confirm.status_code == 400
    assert missing_confirm.get_json()["error"]["code"] == "validation_error"

    still_exists = client.get("/api/auth/me", headers=headers)
    assert still_exists.status_code == 200


def test_profile_delete_removes_account_and_blocks_future_login(client):
    """Delete an authenticated profile and prevent subsequent logins."""
    signup = client.post(
        "/api/auth/signup",
        json={"name": "Delete Me", "email": "delete-me@example.com", "password": "pass1234", "agree_terms": True},
    )
    assert signup.status_code == 201

    login = client.post("/api/auth/login", json={"email": "delete-me@example.com", "password": "pass1234"})
    assert login.status_code == 200
    token = login.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    deleted = client.delete("/api/auth/profile", headers=headers, json={"confirm": "DELETE"})
    assert deleted.status_code == 200
    assert deleted.get_json()["data"]["deleted"] is True

    me_after_delete = client.get("/api/auth/me", headers=headers)
    assert me_after_delete.status_code == 404

    relogin = client.post("/api/auth/login", json={"email": "delete-me@example.com", "password": "pass1234"})
    assert relogin.status_code == 401


def test_avatar_upload_and_read(client):
    """Upload and fetch avatar images through protected endpoints."""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    image_bytes = make_image_bytes()
    upload = client.post(
        "/api/auth/avatar",
        headers=headers,
        data={"image": (io.BytesIO(image_bytes), "avatar.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    avatar = upload.get_json()["data"]["user"]["avatar"]
    assert avatar.startswith("/api/auth/avatar/avatar_u")

    by_header = client.get(avatar, headers=headers)
    assert by_header.status_code == 200

    by_query = client.get(f"{avatar}?token={token}")
    assert by_query.status_code == 200


def test_avatar_upload_and_read_with_relative_upload_dir(client):
    """Serve avatar correctly when UPLOAD_DIR is configured as a relative path."""
    client.application.config["UPLOAD_DIR"] = "backend/uploads"
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    image_bytes = make_image_bytes()
    upload = client.post(
        "/api/auth/avatar",
        headers=headers,
        data={"image": (io.BytesIO(image_bytes), "avatar.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    avatar = upload.get_json()["data"]["user"]["avatar"]
    assert avatar.startswith("/api/auth/avatar/avatar_u")

    by_query = client.get(f"{avatar}?token={token}")
    assert by_query.status_code == 200


def test_avatar_access_is_denied_for_non_owner_non_admin(client, signup_and_login):
    """Prevent cross-user avatar reads to avoid IDOR exposure."""
    owner_token = signup_and_login("owner-avatar@example.com", "pass1234", "Owner Avatar")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    image_bytes = make_image_bytes(color=(10, 100, 210))
    upload = client.post(
        "/api/auth/avatar",
        headers=owner_headers,
        data={"image": (io.BytesIO(image_bytes), "owner.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    avatar = upload.get_json()["data"]["user"]["avatar"]
    assert avatar.startswith("/api/auth/avatar/avatar_u")

    other_token = signup_and_login("other-avatar@example.com", "pass1234", "Other Avatar")
    denied = client.get(avatar, headers={"Authorization": f"Bearer {other_token}"})
    assert denied.status_code == 404
    assert denied.get_json()["error"]["code"] == "not_found"


def test_avatar_invalid_filename_is_rejected(client, auth_token):
    """Reject avatar requests with invalid filename pattern."""
    response = client.get("/api/auth/avatar/not-an-avatar-file.png", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_avatar_returns_404_when_file_disappears_before_send(client, monkeypatch):
    """Return 404 instead of 500 when avatar file is removed after resolution."""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/api/auth/avatar",
        headers=headers,
        data={"image": (io.BytesIO(make_image_bytes()), "avatar.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    avatar = upload.get_json()["data"]["user"]["avatar"]

    def _raise_file_not_found(*_args, **_kwargs):
        raise FileNotFoundError("simulated race during send_file")

    monkeypatch.setattr("backend.auth.send_file", _raise_file_not_found)
    response = client.get(avatar, headers=headers)
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
