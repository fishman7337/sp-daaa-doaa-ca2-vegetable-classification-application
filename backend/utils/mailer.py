"""SMTP helpers for sending security emails."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app


def _is_smtp_configured() -> bool:
    """Execute is smtp configured."""
    return bool(current_app.config.get("SMTP_HOST") and current_app.config.get("SMTP_FROM_EMAIL"))


def send_otp_email(to_email: str, otp_code: str) -> tuple[bool, str | None]:
    """Send one-time-password email. Returns (ok, error_message)."""
    if not _is_smtp_configured():
        return False, "SMTP is not configured"

    host = current_app.config["SMTP_HOST"]
    port = int(current_app.config["SMTP_PORT"])
    username = current_app.config.get("SMTP_USERNAME", "")
    password = current_app.config.get("SMTP_PASSWORD", "")
    from_email = current_app.config["SMTP_FROM_EMAIL"]
    from_name = current_app.config.get("SMTP_FROM_NAME", "VeggieAI Security")
    use_tls = bool(current_app.config.get("SMTP_USE_TLS", True))
    use_ssl = bool(current_app.config.get("SMTP_USE_SSL", False))

    message = EmailMessage()
    message["Subject"] = "Your VeggieAI OTP Code"
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = to_email
    message.set_content(
        f"Your one-time verification code is: {otp_code}\n\n"
        "This code expires in a few minutes. If you did not request it, ignore this email."
    )

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=10) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - exercised in integration
        return False, str(exc)

    return True, None


def send_password_reset_email(to_email: str, reset_link: str, ttl_sec: int) -> tuple[bool, str | None]:
    """Send password reset link email. Returns (ok, error_message)."""
    if not _is_smtp_configured():
        return False, "SMTP is not configured"

    host = current_app.config["SMTP_HOST"]
    port = int(current_app.config["SMTP_PORT"])
    username = current_app.config.get("SMTP_USERNAME", "")
    password = current_app.config.get("SMTP_PASSWORD", "")
    from_email = current_app.config["SMTP_FROM_EMAIL"]
    from_name = current_app.config.get("SMTP_FROM_NAME", "VeggieAI Security")
    use_tls = bool(current_app.config.get("SMTP_USE_TLS", True))
    use_ssl = bool(current_app.config.get("SMTP_USE_SSL", False))

    ttl_minutes = max(1, int(ttl_sec) // 60)
    message = EmailMessage()
    message["Subject"] = "Reset your VeggieAI password"
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = to_email
    message.set_content(
        "We received a request to reset your VeggieAI password.\n\n"
        f"Open this one-time link to reset your password:\n{reset_link}\n\n"
        f"This link expires in about {ttl_minutes} minutes.\n"
        "If you did not request this, you can ignore this email."
    )

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=10) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - exercised in integration
        return False, str(exc)

    return True, None
