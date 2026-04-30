# CI/CD

Primary CI/CD is implemented with GitHub Actions in `.github/workflows/ci.yml`. The GitHub workflow runs from the source tree and excludes presentation and declaration artifacts from the repository.

## Pipeline Stages
- `docs`
- `lint`
- `test`
- `mlops`
- `security`
- `build`
- `deploy` (manual or platform-triggered)

## Job Map

Lint gates:
- `documentation_structure`
- `lint_backend`
- `lint_model_service`
- `lint_docstrings`

Test gates:
- `backend_tests`: unit/api regression suite with coverage threshold (`BACKEND_COVERAGE_MIN`, default `85`)
- `model_service_tests`: model-service suite with coverage threshold (`MODEL_SERVICE_COVERAGE_MIN`, default `85`)

MLOps gates:
- `mlops_model_registry_validate`: validates `models/models.json`, labels/config schema, and emits model checksum report
- `mlops_runtime_smoke`: boots local stack (`python main.py`) and runs:
  - `scripts/smoke_serving.py`
  - `scripts/smoke_webapp.py`

Security gates:
- `backend_security_tests` (`-m security`)
- `backend_e2e_tests` (`-m e2e`)
- `bandit_scan`
- `dependency_audit_python`
- `secret_scan` (`gitleaks`)

Build:
- `build_images` (backend + model_service)

Deploy:
- `render_deploy` (production environment)
  - Auto deploy only when `AUTO_DEPLOY_MAIN=true`
  - Otherwise manual approval on `main`

## Required CI Variables
- `RENDER_BACKEND_DEPLOY_HOOK`
- `RENDER_MODEL_SERVICE_DEPLOY_HOOK`

Optional deployment control:
- `AUTO_DEPLOY_MAIN=true` to make production deploy automatic

Coverage tuning:
- `BACKEND_COVERAGE_MIN`
- `MODEL_SERVICE_COVERAGE_MIN`

## Artifacts
- JUnit reports for test/security/e2e jobs
- Cobertura XML coverage reports for backend/model_service tests
- `reports/model-registry-report.json` (model manifest + checksums + validation result)
- `reports/local-stack.log` from runtime smoke stage

## Deployment Flow
On `main`, production deploy is available only after all gates pass:
1. Documentation structure, lint, tests, and coverage.
2. Model registry validation and runtime smoke checks.
3. Security scans and E2E checks.
4. Docker image builds.
5. Render deploy hooks triggered from a protected environment or manual release process.
