# Model Service

The model service is a small Flask inference API used by local MLOps validation and `/api/predict`.

## Responsibilities

- Load model package metadata from `models/models.json`.
- Validate model labels and preprocessing configuration.
- Expose `/health` and `/predict`.
- Return deterministic local predictions suitable for smoke tests and CI.

## Key Files

- `app.py`: Flask application factory and routes.
- `config.py`: environment-driven settings.
- `models.py`: registry and model prediction abstraction.
- `utils/`: response, logging, and validation helpers.
- `tests/`: model-service pytest suite.

Run:

```bash
pip install -r model_service/requirements-dev.txt
pytest model_service/tests
```
