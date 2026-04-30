# Contributing

VeggieAI is an individual coursework repository. Contributions are expected mainly from the owner, lecturer, or approved reviewers.

## Workflow

1. Create a branch from `develop` or `main` using `feat/`, `fix/`, `docs/`, `test/`, or `chore/`.
2. Keep each change focused and easy to review.
3. Update documentation when behavior, commands, environment variables, APIs, or operations change.
4. Add or update tests for behavior changes.
5. Open a GitHub pull request after local checks pass.

## Local Checks

```bash
ruff check backend main.py
ruff check model_service
ruff format --check backend main.py
ruff format --check model_service
python scripts/check_readmes.py
pytest
python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json
```

## Commit Messages

Use Conventional Commits:

- `feat:` user-facing feature
- `fix:` bug fix
- `docs:` documentation-only change
- `test:` test addition or update
- `chore:` tooling, CI, or maintenance
- `refactor:` internal code change without behavior change

## Review Checklist

- Assignment requirements remain traceable.
- CI, pytest, and MLOps gates are considered.
- New secrets are not committed.
- Each maintained folder has a `README.md`.
- Model changes update registry metadata and governance notes.
- Security-sensitive changes include negative-path tests where practical.
