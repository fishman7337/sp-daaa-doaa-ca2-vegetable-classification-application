"""Validation helpers for model package governance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ALLOWED_NORMALIZE_MODES = {"0-1", "-1-1", "none"}
ALLOWED_CHANNEL_MODES = {"rgb", "grayscale"}


def _sha256(path: Path) -> str:
    """Return SHA-256 digest for a file path."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    """Read a JSON file with strict UTF-8 decoding."""
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_config(config: dict[str, Any], *, model_name: str, errors: list[str]) -> None:
    """Validate model config schema and value ranges."""
    image_size = config.get("image_size")
    if not (
        isinstance(image_size, list)
        and len(image_size) == 2
        and all(isinstance(value, int) and value > 0 for value in image_size)
    ):
        errors.append(f"{model_name}: config.image_size must be a list of two positive integers")

    normalize = str(config.get("normalize", "")).strip()
    if normalize not in ALLOWED_NORMALIZE_MODES:
        errors.append(f"{model_name}: config.normalize must be one of {sorted(ALLOWED_NORMALIZE_MODES)}")

    channels = str(config.get("channels", "")).strip().lower()
    if channels not in ALLOWED_CHANNEL_MODES:
        errors.append(f"{model_name}: config.channels must be one of {sorted(ALLOWED_CHANNEL_MODES)}")

    top_k = config.get("top_k")
    if top_k is not None and (not isinstance(top_k, int) or top_k < 1 or top_k > 10):
        errors.append(f"{model_name}: config.top_k must be an integer between 1 and 10")


def _validate_labels(labels: Any, *, model_name: str, errors: list[str]) -> None:
    """Validate label file structure."""
    if not isinstance(labels, list) or not labels:
        errors.append(f"{model_name}: labels must be a non-empty JSON array")
        return
    for index, value in enumerate(labels):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{model_name}: labels[{index}] must be a non-empty string")


def validate_models_root(models_root: Path, *, require_model_binary: bool = False) -> list[str]:
    """Validate models directory and return a list of governance errors."""
    errors: list[str] = []
    if not models_root.exists():
        return [f"models root does not exist: {models_root}"]
    if not models_root.is_dir():
        return [f"models root is not a directory: {models_root}"]

    manifest_path = models_root / "models.json"
    if not manifest_path.exists():
        return [f"models manifest missing: {manifest_path}"]

    try:
        manifest = _read_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"models manifest is invalid JSON: {exc}"]

    entries = manifest.get("models")
    if not isinstance(entries, list) or not entries:
        return ["models manifest must define a non-empty 'models' array"]

    seen_names: set[str] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"models[{idx}] must be an object")
            continue

        name = str(entry.get("name") or "").strip()
        if not name:
            errors.append(f"models[{idx}].name is required")
            continue
        if name in seen_names:
            errors.append(f"duplicate model name in manifest: {name}")
            continue
        seen_names.add(name)

        relative_dir = str(entry.get("path") or name).strip()
        model_dir = models_root / relative_dir
        if not model_dir.exists() or not model_dir.is_dir():
            errors.append(f"{name}: model directory not found: {model_dir}")
            continue

        labels_filename = str(entry.get("labels") or "labels.json").strip()
        config_filename = str(entry.get("config") or "config.json").strip()
        labels_path = model_dir / labels_filename
        config_path = model_dir / config_filename

        if not labels_path.exists():
            errors.append(f"{name}: labels file missing: {labels_path}")
        if not config_path.exists():
            errors.append(f"{name}: config file missing: {config_path}")

        labels: Any = []
        config: dict[str, Any] = {}
        if labels_path.exists():
            try:
                labels = _read_json(labels_path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{name}: labels file is invalid JSON: {exc}")
        if config_path.exists():
            try:
                raw_config = _read_json(config_path)
                if not isinstance(raw_config, dict):
                    errors.append(f"{name}: config must be a JSON object")
                else:
                    config = raw_config
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{name}: config file is invalid JSON: {exc}")

        if labels_path.exists():
            _validate_labels(labels, model_name=name, errors=errors)
        if config_path.exists() and config:
            _validate_config(config, model_name=name, errors=errors)

        if require_model_binary:
            binary_candidates = [model_dir / "model.h5", model_dir / "model.keras", model_dir / "model.onnx"]
            if not any(path.exists() for path in binary_candidates):
                errors.append(f"{name}: model binary missing (expected one of model.h5, model.keras, model.onnx)")

    return errors


def build_model_manifest(models_root: Path) -> dict[str, Any]:
    """Build a deterministic artifact/checksum manifest for model packages."""
    manifest_path = models_root / "models.json"
    raw_manifest = _read_json(manifest_path)
    records: list[dict[str, Any]] = []
    for entry in raw_manifest.get("models", []):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        model_dir = models_root / str(entry.get("path") or name).strip()
        labels_path = model_dir / str(entry.get("labels") or "labels.json").strip()
        config_path = model_dir / str(entry.get("config") or "config.json").strip()

        record: dict[str, Any] = {
            "name": name,
            "path": str(model_dir.relative_to(models_root)),
            "labels_sha256": _sha256(labels_path) if labels_path.exists() else "",
            "config_sha256": _sha256(config_path) if config_path.exists() else "",
            "labels_count": 0,
            "image_size": None,
            "normalize": None,
            "channels": None,
        }
        if labels_path.exists():
            labels = _read_json(labels_path)
            if isinstance(labels, list):
                record["labels_count"] = len(labels)
        if config_path.exists():
            config = _read_json(config_path)
            if isinstance(config, dict):
                record["image_size"] = config.get("image_size")
                record["normalize"] = config.get("normalize")
                record["channels"] = config.get("channels")

        for candidate in ("model.h5", "model.keras", "model.onnx"):
            path = model_dir / candidate
            if path.exists():
                record["artifact"] = candidate
                record["artifact_sha256"] = _sha256(path)
                break
        else:
            record["artifact"] = ""
            record["artifact_sha256"] = ""

        records.append(record)

    return {
        "models_root": str(models_root),
        "model_count": len(records),
        "models": records,
    }
