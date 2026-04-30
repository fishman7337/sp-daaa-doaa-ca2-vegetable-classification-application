# VeggieAI MLOps Platform

VeggieAI is a Flask-based machine learning operations project for vegetable image classification, price lookup, authenticated prediction history, and optional chatbot assistance. The repository is structured as a coursework-ready application with a backend API, Jinja web UI, model service, model registry, tests, CI/CD gates, security checks, and operational documentation.

## Coursework Context

- Institution: Singapore Polytechnic, School of Computing
- Diploma: Diploma in Applied AI & Analytics
- Module: DevOps & Automation for AI (ST1516), CA2
- Student: Goh Kun Ming, DAAA
- Academic year: AY25/26, Year 2 Semester 2
- Lecturer: Ryan Chia Xueyi
- License: MIT License

## Main Capabilities

- Jinja-rendered web application for login, prediction, price lookup, profile, and history pages.
- Flask backend API for auth, captcha, OTP, prediction records, chat, security headers, and SQLite persistence.
- Separate model service for local registry-based inference smoke tests.
- VegNet model switching for `vegnet-23` and `vegnet-101`.
- Optional OpenAI chatbot and Roboflow camera detection integrations.
- Pytest suite covering unit, API, security, and end-to-end flows.
- CI/CD workflows for linting, testing, coverage, model registry validation, security scanning, Docker builds, and deployment gates.

## Repository Layout

```text
backend/          Flask API, auth, database access, security, business logic
data/             Dataset placeholders and split documentation
db/               SQLite schema and initialization helpers
docs/             Architecture, CI/CD, MLOps, testing, security, runbooks, ADRs
models/           Lightweight model registry packages and manifest
model_service/    Flask model-service API used by local MLOps checks
model_serving/    TensorFlow Serving assets, notebooks, and model export evidence
reports/          Generated reports and evidence outputs
scripts/          Smoke tests, registry validation, RPA helpers
tf_models/        SavedModel artifacts for TensorFlow Serving
webapp/           Jinja templates, static assets, and frontend documentation
```

Every maintained folder has a local `README.md`. Generated/runtime folders are documented at their nearest stable parent and excluded from the documentation gate where appropriate.

## Quick Start

Create and activate a virtual environment, then install development dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
pip install -r model_service/requirements-dev.txt
```

Copy the example environment and adjust secrets:

```bash
copy .env.example .env
```

Run the local stack:

```bash
python main.py
```

Local services:

- Web app and backend API: `http://localhost:5000`
- Model service health: `http://localhost:8000/health`

## Docker Compose

```bash
copy .env.example .env
docker compose up --build
```

Compose starts:

- `backend` on `http://localhost:5000`
- `model_service` on `http://localhost:8000`
- SQLite and upload volumes for local runtime state

## Configuration

Use `.env.example` as the documented baseline. Important settings:

- `SECRET_KEY`, `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- `DATABASE_PATH`, `UPLOAD_DIR`, `MODELS_ROOT`
- `MODEL_SERVICE_URL`, `MODEL_SERVICE_TIMEOUT_SEC`
- `VEGGIE_DEFAULT_MODEL`, `VEGNET_23_URL`, `VEGNET_101_URL`, `VEGNET_REMOTE_ENABLED`
- `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`
- `ROBOFLOW_API_KEY`, `ROBOFLOW_MODEL_ID`, `ROBOFLOW_WORKSPACE`, `ROBOFLOW_WORKFLOW_ID`
- `CAPTCHA_*`, `OTP_*`, `SMTP_*`
- `SECURITY_HEADERS_ENABLED`, `FORCE_HTTPS`, `SESSION_COOKIE_*`, `CSP_POLICY`

Production secrets must be configured in the deployment platform, not committed to the repository.

## Testing

Run the full suite:

```bash
pytest
```

Useful subsets:

```bash
pytest -m unit
pytest -m api
pytest -m security
pytest -m e2e
pytest backend/tests
pytest model_service/tests
```

Quality and MLOps checks:

```bash
ruff check backend model_service scripts main.py
ruff format --check backend model_service scripts main.py
python scripts/check_readmes.py
python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json
python scripts/smoke_serving.py --base-url http://127.0.0.1:8000
python scripts/smoke_webapp.py --base-url http://127.0.0.1:5000
```

## CI/CD And MLOps

Primary automation is defined in `.github/workflows/ci.yml`. In this repository layout, the root workflow runs with `Source-Codes/` as the working directory so only application source, tests, models, and operational docs are part of the GitHub submission.

The CI gates cover:

- Documentation structure check for folder-level READMEs.
- Ruff lint and format checks.
- Backend and model-service pytest suites with coverage artifacts.
- Model registry validation and checksum report generation.
- Runtime smoke checks for the local stack.
- Bandit, pip-audit, and gitleaks security scans.
- Docker image builds for backend and model service.

See `docs/cicd.md`, `docs/mlops.md`, and `docs/model-governance.md` for the operational details.

## API Summary

API responses follow a consistent envelope:

```json
{ "data": {}, "request_id": "..." }
```

or:

```json
{ "error": { "code": "...", "message": "...", "details": {} }, "request_id": "..." }
```

Main endpoints:

- `POST /api/auth/login`
- `POST /api/auth/signup`
- `POST /api/auth/otp/verify`
- `GET /api/auth/me`
- `POST /api/predict`
- `GET /api/models`
- `POST /api/veggie/predict`
- `POST /api/veggie/detect`
- `GET /api/veggie/models`
- `GET /api/veggie/prices`
- `GET /api/veggie/history`
- `POST /api/chat/message`
- `GET /api/chat/history`
- `DELETE /api/chat/history`

Page routes:

- `/`
- `/auth`
- `/predict`
- `/prices`
- `/profile`
- `/history`

## Documentation Map

- `docs/architecture.md`: service layout, data ownership, inference routing.
- `docs/api-contract.md`: API response and route contract.
- `docs/testing.md`: pytest strategy and coverage expectations.
- `docs/security.md`: security design and scanning.
- `docs/cicd.md`: pipeline gates and artifacts.
- `docs/mlops.md`: model registry, promotion, monitoring, rollback.
- `docs/runbooks/`: local development and service runbooks.
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`, `SECURITY.md`: project governance.

## License

This project is released under the MIT License. See `LICENSE`.
