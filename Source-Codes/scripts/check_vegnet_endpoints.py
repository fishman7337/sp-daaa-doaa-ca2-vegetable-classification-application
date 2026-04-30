"""Diagnose VegNet endpoint behavior using local sample images.

Example:
    python scripts/check_vegnet_endpoints.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image, ImageOps

CLASS_NAMES = [
    "Bean",
    "Bitter_Gourd",
    "Brinjal",
    "Cabbage",
    "Capsicum",
    "Cauliflower and Broccoli",
    "Cucumber and Bottle_Gourd",
    "Potato",
    "Pumpkin",
    "Radish and Carrot",
    "Tomato",
]
RESAMPLE_MAP = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


@dataclass(frozen=True)
class ModelTarget:
    """Represent remote model endpoint configuration."""

    name: str
    size: int
    endpoint: str
    resample: str


def _preprocess_image(image_path: Path, size: int, resample: str) -> list[list[list[float]]]:
    """Convert an image into the 2D grayscale tensor expected by VegNet."""
    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)
        image = ImageOps.grayscale(image)
        image = image.resize((size, size), resample=RESAMPLE_MAP[resample])
        pixels = list(image.getdata())

    tensor: list[list[list[float]]] = []
    index = 0
    for _ in range(size):
        row: list[list[float]] = []
        for _ in range(size):
            row.append([float(pixels[index]) / 255.0])
            index += 1
        tensor.append(row)
    return tensor


def _predict(model: ModelTarget, image_path: Path, timeout: int) -> tuple[str, float, int]:
    """Call TensorFlow Serving endpoint and return top-1 prediction."""
    payload = {"instances": [_preprocess_image(image_path, model.size, model.resample)]}
    response = requests.post(model.endpoint, json=payload, timeout=timeout)
    response.raise_for_status()

    body = response.json()
    scores = body.get("predictions", [[]])[0]
    if not isinstance(scores, list) or not scores:
        raise ValueError(f"Model response did not include a score vector: {json.dumps(body)[:280]}")
    top_index = max(range(len(scores)), key=lambda index: scores[index])
    top_score = float(scores[top_index])
    label = CLASS_NAMES[top_index] if top_index < len(CLASS_NAMES) else f"class_{top_index}"
    return label, top_score, len(scores)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="VegNet endpoint diagnostics")
    parser.add_argument(
        "--images-dir",
        default="webapp/app/static/images",
        help="Directory containing sample .jpg images.",
    )
    parser.add_argument(
        "--vegnet23-url",
        default="https://ca2-daaa2b02-p2415691-gohkunming.onrender.com/v1/models/vegnet-23:predict",
        help="VegNet-23 TF Serving predict endpoint.",
    )
    parser.add_argument(
        "--vegnet101-url",
        default="https://ca2-daaa2b02-p2415691-gohkunming.onrender.com/v1/models/vegnet-101:predict",
        help="VegNet-101 TF Serving predict endpoint.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    """Run diagnostics against configured VegNet endpoints."""
    args = _parse_args()
    images_dir = Path(args.images_dir)
    if not images_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {images_dir}")

    targets = [
        ModelTarget(name="vegnet-23", size=23, endpoint=args.vegnet23_url, resample="nearest"),
        ModelTarget(name="vegnet-101", size=101, endpoint=args.vegnet101_url, resample="bicubic"),
    ]
    sample_images = sorted(images_dir.glob("*.jpg"))
    if not sample_images:
        raise FileNotFoundError(f"No .jpg samples found in {images_dir}")

    print("image,model,resample,prediction,confidence,num_scores")
    for image_path in sample_images:
        for model in targets:
            try:
                label, score, num_scores = _predict(model, image_path, timeout=args.timeout)
                print(f"{image_path.name},{model.name},{model.resample},{label},{score:.6f},{num_scores}")
            except Exception as exc:  # noqa: BLE001 - diagnostic script should show all failures.
                print(f"{image_path.name},{model.name},{model.resample},ERROR,{exc},0")


if __name__ == "__main__":
    main()
