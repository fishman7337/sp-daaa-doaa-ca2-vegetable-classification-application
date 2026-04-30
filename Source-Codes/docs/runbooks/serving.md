# Model Serving Runbook

## Responsibilities
- Load two model versions.
- Expose inference endpoint.
- Provide health and model listing endpoints.

## Configuration
- `MODEL_REGISTRY_PATH`
- `MODEL_A_PATH` and `MODEL_B_PATH`
- `LOG_LEVEL`

## Observability
- Log requests and latency.
- Track errors and model selection.

## Deployment checklist
- Build image
- Smoke test /health
- Verify model switch