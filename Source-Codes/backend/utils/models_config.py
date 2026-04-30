"""Model config loader for available model packages."""

from __future__ import annotations

import json
from pathlib import Path


def load_models_config(models_root: str) -> list[dict]:
    """Execute load models config."""
    root = Path(models_root)
    config_path = root / "models.json"
    models: list[dict] = []
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        for entry in data.get("models", []):
            name = entry.get("name")
            if not name:
                continue
            model_dir = root / entry.get("path", name)
            labels_path = model_dir / entry.get("labels", "labels.json")
            labels = []
            if labels_path.exists():
                labels = json.loads(labels_path.read_text(encoding="utf-8"))
            models.append({"name": name, "labels": labels})
        return models
    for model_dir in root.iterdir():
        if not model_dir.is_dir():
            continue
        labels_path = model_dir / "labels.json"
        if labels_path.exists():
            labels = json.loads(labels_path.read_text(encoding="utf-8"))
            models.append({"name": model_dir.name, "labels": labels})
    return models


def model_names(models_root: str) -> set[str]:
    """Execute model names."""
    return {m["name"] for m in load_models_config(models_root)}
