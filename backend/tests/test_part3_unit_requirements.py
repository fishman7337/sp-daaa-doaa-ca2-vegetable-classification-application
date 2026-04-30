"""Part 3 unit tests mapped to explicit quality categories.

This module keeps requirement-driven unit tests readable by grouping checks with
`pytest` markers:
- `validity`
- `range`
- `consistency`
- `expected_failure`
- `unexpected_failure`
"""

from __future__ import annotations

import io

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from backend.utils.validation import read_image_bytes
from backend.veggie import (
    _extract_probability_vector,
    _parse_input_size,
    _preprocess_image_for_tf_serving,
    _resolve_model_input_size,
    _resolve_resize_strategy,
)

from .conftest import make_image_bytes

pytestmark = [pytest.mark.unit]


@pytest.mark.validity
def test_read_image_bytes_accepts_valid_png_payload() -> None:
    """Accept valid PNG input and return bytes, extension, and checksum."""
    image_stream = io.BytesIO(make_image_bytes())
    storage = FileStorage(stream=image_stream, filename="pixel.png", content_type="image/png")

    payload, extension, sha256_hash = read_image_bytes(storage)

    assert payload
    assert extension == "png"
    assert len(sha256_hash) == 64


@pytest.mark.validity
@pytest.mark.expected_failure
@pytest.mark.parametrize(
    ("filename", "content", "expected_error"),
    [
        ("missing.png", None, "image_missing"),
        ("invalid.txt", b"not-an-image", "image_invalid"),
    ],
)
def test_read_image_bytes_rejects_invalid_payloads(filename: str, content: bytes | None, expected_error: str) -> None:
    """Reject missing or malformed uploads with stable error codes."""
    if content is None:
        storage = None
    else:
        storage = FileStorage(stream=io.BytesIO(content), filename=filename)

    with pytest.raises(ValueError) as exc_info:
        read_image_bytes(storage)

    assert str(exc_info.value) == expected_error


@pytest.mark.range
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("23x23", 23),
        ("101x101", 101),
        ("0x0", 23),
        ("-1x-1", 23),
        ("invalid", 23),
    ],
)
def test_parse_input_size_handles_expected_ranges(raw: str, expected: int) -> None:
    """Clamp invalid input sizes to a safe default and parse valid sizes."""
    assert _parse_input_size(raw) == expected


@pytest.mark.range
def test_resolve_model_input_size_enforces_vegnet_dimensions() -> None:
    """Enforce 23x23 for VegNet-23 and 101x101 for VegNet-101."""
    assert _resolve_model_input_size("vegnet-23", "999x999") == 23
    assert _resolve_model_input_size("vegnet-101", "1x1") == 101
    assert _resolve_model_input_size("custom-model", "55x55") == 55


@pytest.mark.range
def test_preprocess_output_shape_and_range(app) -> None:
    """Return a normalized 23x23x1 tensor with values inside `[0, 1]`."""
    image_bytes = make_image_bytes(color=(240, 128, 10))

    with app.app_context():
        matrix = _preprocess_image_for_tf_serving(image_bytes=image_bytes, input_size=23, model_name="vegnet-23")

    assert len(matrix) == 23
    assert all(len(row) == 23 for row in matrix)
    assert all(len(pixel) == 1 for row in matrix for pixel in row)
    assert all(0.0 <= pixel[0] <= 1.0 for row in matrix for pixel in row)


@pytest.mark.consistency
def test_preprocess_is_deterministic_for_identical_input(app) -> None:
    """Produce identical tensors for repeated preprocessing of the same bytes."""
    image_bytes = make_image_bytes(color=(44, 55, 66))

    with app.app_context():
        first = _preprocess_image_for_tf_serving(image_bytes=image_bytes, input_size=23, model_name="vegnet-23")
        second = _preprocess_image_for_tf_serving(image_bytes=image_bytes, input_size=23, model_name="vegnet-23")

    assert first == second


@pytest.mark.consistency
def test_resize_strategy_defaults_match_model_characteristics(app) -> None:
    """Use nearest for VegNet-23 and bicubic for VegNet-101 by default."""
    with app.app_context():
        assert _resolve_resize_strategy("vegnet-23", 23) == Image.Resampling.NEAREST
        assert _resolve_resize_strategy("vegnet-101", 101) == Image.Resampling.BICUBIC


@pytest.mark.expected_failure
def test_extract_probability_vector_rejects_missing_predictions() -> None:
    """Raise a validation error when `predictions` is absent."""
    with pytest.raises(ValueError, match="Missing predictions"):
        _extract_probability_vector({"unexpected": []})


@pytest.mark.unexpected_failure
def test_extract_probability_vector_rejects_non_numeric_values() -> None:
    """Raise a validation error for malformed upstream score vectors."""
    with pytest.raises(ValueError, match="non-numeric"):
        _extract_probability_vector({"predictions": [["bad", object()]]})
