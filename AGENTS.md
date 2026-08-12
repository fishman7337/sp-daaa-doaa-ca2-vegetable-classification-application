# Repository agent instructions

## Scope and precedence

These instructions apply to the entire repository. If a future directory contains a more specific `AGENTS.md`, follow that file for work inside its directory. Direct maintainer instructions take precedence.

## Project context

- **Project:** VeggieAI MLOps Platform
- **Repository shape:** Python, Docker, Jupyter notebooks
- Read `README.md` before changing behaviour, architecture, data handling, or public claims.
- Treat `CONTRIBUTING.md` as the authoritative development workflow and command reference.
- Follow `SECURITY.md` for vulnerability reporting and `CODE_OF_CONDUCT.md` for collaboration.
- Use the workflows under `.github/workflows/` as the final cross-platform CI contract.

## Working agreement

1. Keep each change focused on a clear problem; avoid unrelated cleanup.
2. Inspect nearby tests, configuration, documentation, and generated artifacts before editing.
3. Add or update tests for behavioural changes, including failure and boundary cases.
4. Preserve public APIs and file formats unless the change explicitly includes a documented migration.
5. Never commit credentials, personal data, local environments, caches, or unlicensed datasets.
6. Do not weaken lint, coverage, security, or dependency gates merely to obtain a passing run.
7. After code or architecture changes, run `graphify update .` and review the graph diff; do not commit cache-only churn.
8. Do not stage, commit, push, or publish changes unless the maintainer explicitly requests that action.

## Required validation

Run commands from the repository root. Use a clean environment when dependency or packaging behaviour changes.

### Standard development gate

```text
python -m venv .venv
python -m pip install -r backend/requirements-dev.txt
python -m pip install -r model_service/requirements-dev.txt
python -m ruff check .
python -m ruff format --check .
python -m pytest backend/tests
python -m pytest model_service/tests
python -m compileall backend db main.py model_service scripts webapp
```

### Repository-specific CI-equivalent checks

```text
python scripts/check_readmes.py
python -m ruff check backend main.py model_service
python -m ruff format --check backend main.py model_service
python -m pytest backend/tests --cov=backend --cov-fail-under=85
python -m pytest model_service/tests --cov=model_service --cov-fail-under=85
python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json
python -m bandit -r backend model_service -x backend/tests,model_service/tests -ll -ii -s B104
python -m pip_audit -r backend/requirements-dev.txt
python -m pip_audit -r model_service/requirements-dev.txt
docker build -f backend/Dockerfile -t veggieai/backend:ci .
docker build -f model_service/Dockerfile -t veggieai/model-service:ci .
```

Also run `git diff --check`. Record exactly which commands ran, their outcomes, and any documented prerequisite that prevented a check. Do not describe an unexecuted check as passing.

### Conditional or integration setup

- Run `python main.py` or `docker compose up --build` only when starting the local backend and model-service stack.
- Run live service smoke scripts only after both documented local services are healthy.

## Managed artifacts and data

- Treat `models/models.json` and the committed model packages as governed registry inputs; validate changes with `scripts/validate_model_registry.py` and review the generated report.
- Keep runtime datasets, databases, uploads, logs, and generated reports out of Git unless explicitly documented as maintained evidence.

## Integration and claim boundaries

- OpenAI, Roboflow, SMTP, remote-model, and deployment settings are optional integrations whose secrets belong in the environment or deployment platform.
- Local stack smoke tests require both the backend and model service; optional live detection is not a production-latency result.
- Container changes must preserve the documented backend and model-service build contexts and security posture.
- **Verified local capability:** 216 backend, 22 model, and 2 registry tests plus live service smokes.
- **Known boundary:** Optional Roboflow integration is not a production-latency result.

## Code, documentation, and evidence standards

- For Python, follow PEP 8, PEP 257, and Google-style docstrings in the production scopes configured by Ruff.
- Prefer small, typed, testable units and explicit error handling. Avoid silent fallbacks that hide invalid data, missing models, credentials, or services.
- Update README, architecture, data/model documentation, examples, and changelog material when interfaces or behaviour change.
- Every quantitative claim must retain its denominator, dataset/version, split, date range, run/configuration, and calculation method.
- Distinguish measured results from targets, examples, heuristics, previews, and prior runs. Do not infer deployment, accuracy, security, causality, or impact from tests or scaffolding alone.
- Update generated files through their source script. If no generator exists, document the manual process and verify semantic equivalence.

## Review and handoff

Before handing off a change, provide a concise summary, list changed files, report validation evidence, and call out residual risks or unavailable integrations. Keep commits imperative and scoped; do not add tool-attribution or automated co-author trailers.
