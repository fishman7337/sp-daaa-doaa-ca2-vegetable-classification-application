# Release Process

VeggieAI uses semantic versioning for tagged releases.

## Versioning

- `MAJOR`: incompatible API, model registry, or deployment changes.
- `MINOR`: backwards-compatible features or new model packages.
- `PATCH`: bug fixes, documentation, security, and CI changes.

## Release Checklist

1. Confirm all CI gates pass on `main`.
2. Update `CHANGELOG.md`.
3. Run `pytest`.
4. Run `python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json`.
5. Build Docker images locally if deployment changed.
6. Tag the release as `vMAJOR.MINOR.PATCH`.
7. Store deployment evidence in `docs/evidence/` or `reports/`.

## Hotfix Checklist

1. Branch from `main`.
2. Apply the smallest safe fix.
3. Add or update tests.
4. Run targeted checks.
5. Merge after CI passes.
6. Tag a patch release if deployed.
