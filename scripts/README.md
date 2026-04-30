# Scripts

Utility scripts for documentation governance, MLOps validation, smoke checks, and optional UI automation.

## Scripts

- `check_readmes.py`: verifies that maintained folders include local `README.md` files.
- `validate_model_registry.py`: validates model package metadata and emits checksum reports.
- `smoke_serving.py`: checks model-service `/health` and `/predict`.
- `smoke_webapp.py`: checks backend `/api/health`, `/api/models`, `/`, and `/auth`.
- `check_vegnet_endpoints.py`: diagnoses VegNet endpoint predictions using local sample images.
- `rpa_test.py`: optional Selenium-based frontend RPA flow.
- `uipath/`: UiPath coded workflow assets for frontend E2E evidence.

Run scripts from the repository root unless a script says otherwise.
