"""Input validation helpers."""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Tuple

from PIL import Image

ALLOWED_EXTS = {"png", "jpg", "jpeg", "bmp", "gif"}


def read_image_bytes(file_storage) -> Tuple[bytes, str, str]:
    """Validate an uploaded image and return bytes, extension, and sha256."""
    if file_storage is None:
        raise ValueError("image_missing")
    data = file_storage.read()
    if not data:
        raise ValueError("image_empty")
    try:
        img = Image.open(BytesIO(data))
        img.verify()
    except Exception as exc:
        raise ValueError("image_invalid") from exc
    img = Image.open(BytesIO(data))
    fmt = (img.format or "png").lower()
    ext = "jpg" if fmt == "jpeg" else fmt
    if ext not in ALLOWED_EXTS:
        raise ValueError("image_unsupported")
    sha256 = hashlib.sha256(data).hexdigest()
    return data, ext, sha256
