"""Model registry and preprocessing utilities."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .utils.logging import log_event

logger = logging.getLogger(__name__)

DEFAULT_LABELS = ["class_0", "class_1", "class_2", "class_3"]


def _load_json(path: Path, default: Any) -> Any:
    """Execute load json."""
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(arr: np.ndarray, mode: str) -> np.ndarray:
    """Execute normalize."""
    if mode == "0-1":
        return arr / 255.0
    if mode == "-1-1":
        return (arr / 127.5) - 1.0
    return arr


def preprocess_image(image_bytes: bytes, config: dict) -> np.ndarray:
    """Execute preprocess image."""
    img = Image.open(BytesIO(image_bytes))
    channels = config.get("channels", "rgb")
    if channels == "grayscale":
        img = img.convert("L")
    else:
        img = img.convert("RGB")
    size = config.get("image_size", [224, 224])
    img = img.resize((int(size[0]), int(size[1])))
    arr = np.array(img).astype("float32")
    arr = _normalize(arr, config.get("normalize", "0-1"))
    if channels == "grayscale":
        arr = np.expand_dims(arr, axis=-1)
    return arr


class DeterministicModel:
    """Represent DeterministicModel."""

    def __init__(self, labels: list[str]) -> None:
        """Execute init."""
        self.labels = labels or DEFAULT_LABELS

    def predict(self, image_array: np.ndarray, sha256: str, top_k: int) -> list[dict]:
        """Execute predict."""
        seed = int(sha256[:8], 16)
        rng = random.Random(seed)
        scores = [rng.random() for _ in self.labels]
        total = sum(scores) or 1.0
        probs = [score / total for score in scores]
        ranked = sorted(zip(self.labels, probs, strict=False), key=lambda item: item[1], reverse=True)
        result = [
            {"label": label, "confidence": round(conf, 6)} for label, conf in ranked[: max(1, min(top_k, len(ranked)))]
        ]
        return result


@dataclass
class ModelPackage:
    """Represent ModelPackage."""

    name: str
    root: Path
    mode: str
    labels: list[str]
    config: dict
    model: Any

    @classmethod
    def load(cls, name: str, root: Path, mode: str) -> "ModelPackage":
        """Execute load."""
        labels = _load_json(root / "labels.json", DEFAULT_LABELS)
        config = _load_json(
            root / "config.json",
            {"image_size": [224, 224], "normalize": "0-1", "channels": "rgb"},
        )
        model = cls._load_model(root, mode, labels)
        return cls(name=name, root=root, mode=mode, labels=labels, config=config, model=model)

    @staticmethod
    def _load_model(root: Path, mode: str, labels: list[str]):
        """Execute load model."""
        if mode == "mock":
            return DeterministicModel(labels)
        model_path = root / "model.h5"
        if not model_path.exists():
            return DeterministicModel(labels)
        try:
            import tensorflow as tf
        except ImportError:
            log_event(logger, "tensorflow_missing", model=str(model_path))
            return DeterministicModel(labels)
        return tf.keras.models.load_model(model_path)

    def predict(self, image_bytes: bytes, top_k: int) -> dict:
        """Execute predict."""
        image_array = preprocess_image(image_bytes, self.config)
        sha256 = hashlib.sha256(image_bytes).hexdigest()
        start = time.perf_counter()
        if isinstance(self.model, DeterministicModel):
            topk = self.model.predict(image_array, sha256, top_k)
        else:
            preds = self.model.predict(np.expand_dims(image_array, axis=0))[0]
            ranked = sorted(zip(self.labels, preds, strict=False), key=lambda item: item[1], reverse=True)
            topk = [
                {"label": label, "confidence": float(score)}
                for label, score in ranked[: max(1, min(top_k, len(ranked)))]
            ]
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        top1 = topk[0]
        return {
            "model_name": self.name,
            "top1_label": top1["label"],
            "top1_conf": float(top1["confidence"]),
            "topk": topk,
            "latency_ms": latency_ms,
        }


class ModelRegistry:
    """Represent ModelRegistry."""

    def __init__(self, models_root: str, mode: str) -> None:
        """Execute init."""
        self.models_root = Path(models_root)
        self.mode = mode
        self.models: dict[str, ModelPackage] = {}

    def load(self) -> None:
        """Execute load."""
        if not self.models_root.exists():
            return
        for model_dir in self.models_root.iterdir():
            if not model_dir.is_dir():
                continue
            labels_path = model_dir / "labels.json"
            if not labels_path.exists():
                continue
            package = ModelPackage.load(model_dir.name, model_dir, self.mode)
            self.models[package.name] = package
            log_event(logger, "model_loaded", model=package.name, mode=self.mode)

    def list_models(self) -> list[str]:
        """Execute list models."""
        return sorted(self.models.keys())

    def get(self, name: str) -> ModelPackage | None:
        """Execute get."""
        return self.models.get(name)
