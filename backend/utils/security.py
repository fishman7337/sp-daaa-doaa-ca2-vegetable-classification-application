"""Security helpers for password hashing and seeding users."""

import logging

import bcrypt

from ..repository import create_user, get_user_by_username
from .logging import log_event

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Execute hash password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Execute verify password."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def seed_admin(db, username: str, password: str) -> None:
    """Execute seed admin."""
    if get_user_by_username(db, username):
        return
    create_user(db, username, hash_password(password), role="admin")
    log_event(logger, "seed_admin", username=username)
