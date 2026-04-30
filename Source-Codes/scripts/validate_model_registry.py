"""Validate model registry structure and emit a model-governance manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model_service.utils.model_validation import build_model_manifest, validate_models_root


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate models/ registry for CI/CD gates.")
    parser.add_argument(
        "--models-root",
        default="models",
        help="Path to the models directory (default: models).",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Optional JSON output path for checksum manifest and validation result.",
    )
    parser.add_argument(
        "--require-model-binary",
        action="store_true",
        help="Require one model artifact file per model package (model.h5/model.keras/model.onnx).",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    models_root = Path(args.models_root).expanduser().resolve()

    errors = validate_models_root(
        models_root=models_root,
        require_model_binary=bool(args.require_model_binary),
    )
    manifest = {}
    if not errors:
        manifest = build_model_manifest(models_root)

    report_payload = {
        "ok": not errors,
        "errors": errors,
        "manifest": manifest,
    }

    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    if errors:
        print("MODEL REGISTRY VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Model registry validation passed for {models_root}")
    print(f"Validated model packages: {report_payload['manifest']['model_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
