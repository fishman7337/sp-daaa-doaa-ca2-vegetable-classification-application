"""Unit tests for secure uploaded-file path resolution helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.utils.files import resolve_uploaded_file_path

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_resolve_uploaded_file_path_accepts_current_filename(tmp_path: Path):
    """Resolve current-format stored refs like '<sha>.jpg'."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    target = upload_root / "abc123.jpg"
    target.write_bytes(b"image-bytes")

    resolved = resolve_uploaded_file_path(upload_root, "abc123.jpg")
    assert resolved == target.resolve()


def test_resolve_uploaded_file_path_supports_legacy_backend_upload_prefix(tmp_path: Path):
    """Resolve legacy refs that include 'backend/uploads/' prefix."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    target = upload_root / "legacy.png"
    target.write_bytes(b"legacy-image")

    resolved = resolve_uploaded_file_path(upload_root, "backend/uploads/legacy.png")
    assert resolved == target.resolve()


def test_resolve_uploaded_file_path_normalizes_windows_style_separators(tmp_path: Path):
    """Normalize backslash separators before resolving files under upload root."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    target = upload_root / "avatars" / "u1.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"avatar")

    resolved = resolve_uploaded_file_path(upload_root, r"avatars\u1.png")
    assert resolved == target.resolve()


def test_resolve_uploaded_file_path_rejects_traversal_and_outside_files(tmp_path: Path):
    """Reject traversal attempts and absolute paths outside upload root."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)

    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"not-allowed")

    assert resolve_uploaded_file_path(upload_root, "../outside.jpg") is None
    assert resolve_uploaded_file_path(upload_root, str(outside.resolve())) is None


@pytest.mark.parametrize("raw_ref", [None, "", "   ", "./"])
def test_resolve_uploaded_file_path_rejects_empty_refs(tmp_path: Path, raw_ref: str | None):
    """Return None for missing or empty upload references."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    assert resolve_uploaded_file_path(upload_root, raw_ref) is None
