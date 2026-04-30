"""Runtime smoke test for backend and frontend page availability."""

from __future__ import annotations

import argparse
import time
from typing import Any

import requests


def _wait_for_backend(base_url: str, timeout_sec: int) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_error = ""
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url.rstrip('/')}/api/health", timeout=5)
            if response.status_code == 200:
                payload = response.json()
                return payload.get("data", payload)
            last_error = f"status={response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(1.0)
    raise TimeoutError(f"backend health did not become ready ({last_error})")


def _assert_page_ok(base_url: str, path: str) -> None:
    response = requests.get(f"{base_url.rstrip('/')}{path}", timeout=10)
    if response.status_code != 200:
        raise RuntimeError(f"page smoke failed for {path}: status={response.status_code}")
    if "VeggieAI" not in response.text:
        raise RuntimeError(f"page smoke failed for {path}: expected VeggieAI marker text")


def run(base_url: str, wait_seconds: int) -> None:
    health_payload = _wait_for_backend(base_url, wait_seconds)
    models = health_payload.get("models")
    if not isinstance(models, list) or not models:
        raise RuntimeError("backend /api/health returned no model names")

    models_resp = requests.get(f"{base_url.rstrip('/')}/api/models", timeout=10)
    if models_resp.status_code != 200:
        raise RuntimeError(f"/api/models failed with status={models_resp.status_code}")
    models_payload = models_resp.json().get("data", {})
    api_models = models_payload.get("models", [])
    if not api_models:
        raise RuntimeError("/api/models returned empty model list")

    _assert_page_ok(base_url, "/")
    _assert_page_ok(base_url, "/auth")

    print(
        "backend/web smoke passed:",
        f"models={len(api_models)}",
        f"health_models={len(models)}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for backend and webapp routes.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--wait-seconds", type=int, default=60)
    args = parser.parse_args()

    run(base_url=args.base_url, wait_seconds=max(args.wait_seconds, 5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
