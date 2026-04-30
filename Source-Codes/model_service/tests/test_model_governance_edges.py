"""Additional model-service edge coverage for CI quality gates."""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from model_service.models import DeterministicModel, ModelPackage, ModelRegistry, preprocess_image
from model_service.utils.model_validation import build_model_manifest, validate_models_root

pytestmark = [pytest.mark.unit]


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _image_bytes() -> bytes:
    image = Image.new("RGB", (8, 8), color=(10, 20, 30))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_preprocess_image_grayscale_and_normalize_modes():
    """Cover grayscale conversion and all normalization modes."""
    grayscale = preprocess_image(_image_bytes(), {"image_size": [4, 4], "channels": "grayscale", "normalize": "-1-1"})
    raw = preprocess_image(_image_bytes(), {"image_size": [4, 4], "channels": "rgb", "normalize": "none"})

    assert grayscale.shape == (4, 4, 1)
    assert np.min(grayscale) >= -1.0
    assert np.max(grayscale) <= 1.0
    assert raw.shape == (4, 4, 3)
    assert np.max(raw) > 1.0


def test_model_package_loads_defaults_and_predicts(tmp_path: Path):
    """Load a package without metadata and fall back to deterministic defaults."""
    package = ModelPackage.load("fallback", tmp_path, "mock")
    result = package.predict(_image_bytes(), top_k=2)

    assert package.labels
    assert result["model_name"] == "fallback"
    assert len(result["topk"]) == 2
    assert result["top1_label"] in package.labels


def test_model_registry_ignores_missing_roots_and_non_model_dirs(tmp_path: Path):
    """Handle empty registries and skip directories without labels."""
    missing_registry = ModelRegistry(str(tmp_path / "missing"), "mock")
    missing_registry.load()
    assert missing_registry.list_models() == []
    assert missing_registry.get("anything") is None

    root = tmp_path / "models"
    (root / "not_a_model").mkdir(parents=True)
    registry = ModelRegistry(str(root), "mock")
    registry.load()
    assert registry.list_models() == []


def test_deterministic_model_clamps_top_k():
    """Clamp top_k into a valid range for deterministic predictions."""
    model = DeterministicModel(["a", "b"])
    result = model.predict(np.zeros((2, 2, 3)), "abcdef123456", 99)
    assert [item["label"] for item in result] == ["b", "a"]


def test_model_validation_rejects_manifest_and_package_edge_cases(tmp_path: Path):
    """Exercise invalid manifest, duplicate, missing binary, labels, and config paths."""
    root = tmp_path / "models"
    assert validate_models_root(root) == [f"models root does not exist: {root}"]

    root.write_text("not-a-dir", encoding="utf-8")
    assert validate_models_root(root) == [f"models root is not a directory: {root}"]
    root.unlink()
    root.mkdir()

    (root / "models.json").write_text("{bad", encoding="utf-8")
    assert validate_models_root(root)[0].startswith("models manifest is invalid JSON")

    _write_json(root / "models.json", {"models": []})
    assert validate_models_root(root) == ["models manifest must define a non-empty 'models' array"]

    _write_json(
        root / "models.json",
        {
            "models": [
                "bad-entry",
                {"name": ""},
                {"name": "model_a", "path": "missing"},
                {"name": "model_a", "path": "duplicate"},
                {"name": "model_b", "path": "model_b"},
            ]
        },
    )
    model_b = root / "model_b"
    model_b.mkdir()
    _write_json(model_b / "labels.json", ["ok", ""])
    _write_json(model_b / "config.json", [])

    errors = validate_models_root(root, require_model_binary=True)
    assert any("models[0] must be an object" in error for error in errors)
    assert any("models[1].name is required" in error for error in errors)
    assert any("model_a: model directory not found" in error for error in errors)
    assert any("duplicate model name" in error for error in errors)
    assert any("labels[1]" in error for error in errors)
    assert any("config must be a JSON object" in error for error in errors)
    assert any("model binary missing" in error for error in errors)


def test_build_model_manifest_includes_artifact_checksum(tmp_path: Path):
    """Include optional binary artifact metadata in governance manifests."""
    root = tmp_path / "models"
    _write_json(root / "models.json", {"models": [{"name": "model_a", "path": "model_a"}]})
    _write_json(root / "model_a" / "labels.json", ["a", "b"])
    _write_json(root / "model_a" / "config.json", {"image_size": [2, 2], "normalize": "0-1", "channels": "rgb"})
    (root / "model_a" / "model.onnx").write_bytes(b"model-bytes")

    manifest = build_model_manifest(root)
    record = manifest["models"][0]
    assert record["artifact"] == "model.onnx"
    assert record["artifact_sha256"]
    assert record["labels_count"] == 2
