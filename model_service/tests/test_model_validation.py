"""Unit tests for model registry governance validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from model_service.utils.model_validation import build_model_manifest, validate_models_root

pytestmark = [pytest.mark.unit]


def _write(path: Path, payload) -> None:
    """Write JSON payload to a test file path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_valid_models(tmp_path: Path) -> Path:
    """Create a valid synthetic models directory for governance tests."""
    root = tmp_path / "models"
    _write(
        root / "models.json",
        {
            "models": [
                {"name": "model_a", "path": "model_a", "labels": "labels.json", "config": "config.json"},
                {"name": "model_b", "path": "model_b", "labels": "labels.json", "config": "config.json"},
            ]
        },
    )
    _write(root / "model_a" / "labels.json", ["carrot", "tomato"])
    _write(root / "model_a" / "config.json", {"image_size": [224, 224], "normalize": "0-1", "channels": "rgb"})
    _write(root / "model_b" / "labels.json", ["potato"])
    _write(
        root / "model_b" / "config.json",
        {"image_size": [96, 96], "normalize": "-1-1", "channels": "grayscale"},
    )
    return root


def test_validate_models_root_success(tmp_path: Path):
    """Accept a valid manifest and emit checksums for each model package."""
    root = _seed_valid_models(tmp_path)
    errors = validate_models_root(root)
    assert errors == []

    manifest = build_model_manifest(root)
    assert manifest["model_count"] == 2
    names = {item["name"] for item in manifest["models"]}
    assert names == {"model_a", "model_b"}
    assert all(item["labels_sha256"] for item in manifest["models"])
    assert all(item["config_sha256"] for item in manifest["models"])


def test_validate_models_root_missing_labels(tmp_path: Path):
    """Reject model entries that do not provide labels metadata."""
    root = _seed_valid_models(tmp_path)
    (root / "model_a" / "labels.json").unlink()
    errors = validate_models_root(root)
    assert any("model_a: labels file missing" in item for item in errors)


def test_validate_models_root_rejects_invalid_config(tmp_path: Path):
    """Reject invalid preprocessing config schema/values."""
    root = _seed_valid_models(tmp_path)
    _write(
        root / "model_b" / "config.json",
        {"image_size": [0, 96], "normalize": "weird", "channels": "lab"},
    )
    errors = validate_models_root(root)
    assert any("config.image_size" in item for item in errors)
    assert any("config.normalize" in item for item in errors)
    assert any("config.channels" in item for item in errors)
