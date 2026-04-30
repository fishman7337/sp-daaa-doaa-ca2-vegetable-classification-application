"""File-path utilities for resolving uploaded assets safely."""

from __future__ import annotations

from pathlib import Path


def _is_within(child: Path, parent: Path) -> bool:
    """Return ``True`` when ``child`` is inside ``parent``."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_uploaded_file_path(upload_dir: Path, raw_ref: str | None) -> Path | None:
    """Resolve a stored upload reference to an existing file within ``upload_dir``.

    Supports current refs like ``<sha>.jpg`` and legacy refs like
    ``backend/uploads/<sha>.jpg`` while preventing path traversal outside the
    configured upload directory.
    """
    if not raw_ref:
        return None

    upload_root = upload_dir.expanduser().resolve()
    normalized = str(raw_ref).strip().replace("\\", "/").lstrip("./")
    if not normalized:
        return None

    refs: list[Path] = []
    refs.append(Path(normalized))
    basename = Path(normalized).name
    if basename:
        refs.append(Path(basename))

    lower = normalized.lower()
    marker = "uploads/"
    idx = lower.find(marker)
    if idx >= 0:
        suffix = normalized[idx + len(marker) :].lstrip("/")
        if suffix:
            refs.append(Path(suffix))

    candidates: list[Path] = []
    for ref in refs:
        if ref.is_absolute():
            candidates.append(ref)
        else:
            candidates.append(upload_root / ref)

    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue

        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)

        if not _is_within(resolved, upload_root):
            continue
        if resolved.exists() and resolved.is_file():
            return resolved

    return None
