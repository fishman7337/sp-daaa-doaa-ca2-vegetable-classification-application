# MLOps

VeggieAI uses lightweight MLOps controls that are suitable for a coursework project while still reflecting production habits: registry validation, deterministic tests, smoke checks, checksum reports, deployment gates, and rollback notes.

## Model Package Contract
Each model package under `models/` must provide:
- `labels.json`: non-empty list of labels
- `config.json`: preprocessing config (`image_size`, `normalize`, `channels`)
- Optional model artifact (`model.h5`, `model.keras`, or `model.onnx`)

The source-of-truth manifest is `models/models.json`.

## CI Governance Gate
Pipeline job `mlops_model_registry_validate` runs:
```bash
python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json
```

This enforces:
- manifest integrity
- duplicate model-name rejection
- required labels/config presence
- schema and value checks for preprocessing config

It also emits a checksum manifest for:
- labels file (`labels_sha256`)
- config file (`config_sha256`)
- model artifact (`artifact_sha256`, when present)

## Runtime Smoke Gate
Pipeline job `mlops_runtime_smoke` starts the stack and verifies:
- model service `/health` + `/predict`
- backend `/api/health` + `/api/models`
- frontend entry pages (`/`, `/auth`)

Scripts used:
- `scripts/smoke_serving.py`
- `scripts/smoke_webapp.py`

## Local Verification
```bash
python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json
python main.py
python scripts/smoke_serving.py --base-url http://127.0.0.1:8000
python scripts/smoke_webapp.py --base-url http://127.0.0.1:5000
```

## Promotion Checklist
1. Update model package (`labels.json`, `config.json`, artifact).
2. Update `models/models.json`.
3. Run validation + smoke locally.
4. Record model-card notes in `docs/model-governance.md` if behavior or data changes.
5. Open a GitHub pull request and pass CI gates.
6. Deploy to production from `main` using a protected manual gate unless explicitly automated.

## Rollback Checklist
1. Identify the last healthy model package and deployment.
2. Revert `models/models.json` or deployment endpoint variables.
3. Run `scripts/validate_model_registry.py`.
4. Run smoke checks against the restored service.
5. Record the incident and corrective action in `reports/` or `docs/evidence/`.
