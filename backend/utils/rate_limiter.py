"""Simple in-memory rate limiter for login attempts."""

import time


class LoginRateLimiter:
    """Represent LoginRateLimiter."""

    def __init__(self, max_attempts: int, window_sec: int) -> None:
        """Execute init."""
        self.max_attempts = max_attempts
        self.window_sec = window_sec
        self.attempts: dict[str, list[float]] = {}

    def _prune(self, key: str, now: float) -> None:
        """Execute prune."""
        timestamps = self.attempts.get(key, [])
        self.attempts[key] = [t for t in timestamps if now - t <= self.window_sec]

    def is_blocked(self, key: str) -> bool:
        """Execute is blocked."""
        now = time.time()
        self._prune(key, now)
        return len(self.attempts.get(key, [])) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        """Execute record failure."""
        now = time.time()
        self._prune(key, now)
        self.attempts.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        """Execute reset."""
        self.attempts.pop(key, None)
