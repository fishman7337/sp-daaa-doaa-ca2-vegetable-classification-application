"""Tests for the coordinated local service runner."""

from __future__ import annotations

from typing import Any

import pytest

import main as main_runner


class FakeProcess:
    """Minimal subprocess double with observable shutdown state."""

    def __init__(self, exit_code: int | None) -> None:
        """Initialise the process with its current exit code."""
        self.exit_code = exit_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        """Return the configured process status."""
        return self.exit_code

    def terminate(self) -> None:
        """Record graceful termination and mark the process stopped."""
        self.terminated = True
        self.exit_code = 0

    def kill(self) -> None:
        """Record forced termination and mark the process stopped."""
        self.killed = True
        self.exit_code = -9


def test_main_fails_when_a_managed_service_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a failure exit code if either managed service exits unexpectedly."""
    stopped = FakeProcess(0)
    running = FakeProcess(None)
    processes = iter([stopped, running])

    def fake_spawn(*_args: Any, **_kwargs: Any) -> FakeProcess:
        """Return the next prepared process double."""
        return next(processes)

    monkeypatch.setattr(main_runner, "_spawn", fake_spawn)
    monkeypatch.setattr(main_runner.time, "sleep", lambda _seconds: None)

    with pytest.raises(SystemExit, match="1"):
        main_runner.main()

    assert running.terminated
    assert not running.killed
