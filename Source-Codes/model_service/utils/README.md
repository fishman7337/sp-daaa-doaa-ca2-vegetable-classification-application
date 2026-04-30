# Model Service Utilities

Shared helpers for the model service.

## Modules

- `logging.py`: service logging configuration.
- `model_validation.py`: model registry schema and checksum validation.
- `responses.py`: consistent JSON response envelopes.

Keep these helpers independent from the backend package so the model service can run as a separate container.
