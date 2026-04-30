"""Configuration loader for the model service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get_int(name: str, default: int) -> int:
    """Execute get int."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    """Represent Settings."""

    MODELS_ROOT: str
    MODEL_MODE: str
    MAX_CONTENT_LENGTH: int
    LOG_LEVEL: str
    DEFAULT_TOP_K: int

    def to_dict(self) -> dict:
        """Execute to dict."""
        return self.__dict__


def load_settings() -> Settings:
    """Execute load settings."""
    repo_root = Path(__file__).resolve().parents[1]
    default_models_root = repo_root / "models"
    return Settings(
        MODELS_ROOT=os.getenv("MODELS_ROOT", str(default_models_root)),
        MODEL_MODE=os.getenv("MODEL_MODE", "auto"),
        MAX_CONTENT_LENGTH=_get_int("MAX_CONTENT_LENGTH", 8 * 1024 * 1024),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        DEFAULT_TOP_K=_get_int("DEFAULT_TOP_K", 3),
    )
