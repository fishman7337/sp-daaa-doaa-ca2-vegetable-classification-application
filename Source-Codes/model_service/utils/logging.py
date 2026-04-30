"""Structured logging helpers."""

import json
import logging
import time


def configure_logging(level: str) -> None:
    """Execute configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
    )


def log_event(logger: logging.Logger, event: str, **kwargs) -> None:
    """Execute log event."""
    payload = {
        "event": event,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    payload.update(kwargs)
    logger.info(json.dumps(payload, ensure_ascii=True))
