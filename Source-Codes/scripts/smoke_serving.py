"""Runtime smoke test for the model-service API."""

from __future__ import annotations

import argparse
import base64
import io
import time
from typing import Any

import requests
from PIL import Image


def _make_image_b64() -> str:
    image = Image.new("RGB", (48, 48), color=(18, 163, 82))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _wait_for_health(base_url: str, timeout_sec: int) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_error = ""
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
            if response.status_code == 200:
                payload = response.json()
                return payload.get("data", payload)
            last_error = f"status={response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(1.0)
    raise TimeoutError(f"model-service health did not become ready ({last_error})")


def run(base_url: str, model_name: str, wait_seconds: int) -> None:
    health_payload = _wait_for_health(base_url, wait_seconds)
    models = health_payload.get("models") or []
    if model_name not in models:
        raise RuntimeError(f"model '{model_name}' not loaded. Available: {models}")

    response = requests.post(
        f"{base_url.rstrip('/')}/predict",
        json={
            "model_name": model_name,
            "top_k": 3,
            "image_base64": _make_image_b64(),
        },
        timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError(f"/predict smoke failed with status={response.status_code}: {response.text[:200]}")

    payload = response.json()
    prediction = payload.get("data", payload)
    if not isinstance(prediction, dict):
        raise RuntimeError("model-service response missing data payload")
    for key in ("model_name", "top1_label", "top1_conf", "topk", "latency_ms"):
        if key not in prediction:
            raise RuntimeError(f"model-service response missing required key: {key}")

    print(
        "model-service smoke passed:",
        f"model={prediction['model_name']}",
        f"top1={prediction['top1_label']}",
        f"conf={prediction['top1_conf']}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for model-service runtime readiness.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model-name", default="model_a")
    parser.add_argument("--wait-seconds", type=int, default=60)
    args = parser.parse_args()

    run(base_url=args.base_url, model_name=args.model_name, wait_seconds=max(args.wait_seconds, 5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
