"""Validate that maintained project folders include local README files."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    ".gitlab",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

EXCLUDED_RELATIVE_PATHS = {
    ".dist",
    "backend/uploads",
    "backend/uploads/avatars",
    "presentation",
    "webapp/instance",
}

EXCLUDED_PREFIXES = (
    "tf_models/vegnet-101/1",
    "tf_models/vegnet-23/1",
)


def _to_posix_relative(path: Path, root: Path) -> str:
    """Return a path relative to `root` using POSIX separators."""
    return path.relative_to(root).as_posix()


def _is_excluded(path: Path, root: Path) -> bool:
    """Return whether a directory is generated, cached, or runtime-only."""
    if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
        return True

    rel = _to_posix_relative(path, root)
    if rel in EXCLUDED_RELATIVE_PATHS:
        return True
    return any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def find_missing_readmes(root: Path = REPO_ROOT) -> list[str]:
    """Return maintained directories that do not contain `README.md`."""
    missing: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_dir()):
        if _is_excluded(path, root):
            continue
        if not (path / "README.md").exists():
            missing.append(_to_posix_relative(path, root))
    return missing


def main() -> int:
    """Run the README structure check as a CLI."""
    missing = find_missing_readmes(REPO_ROOT)
    if missing:
        print("The following maintained folders are missing README.md:")
        for folder in missing:
            print(f"- {folder}")
        return 1

    print("README structure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
