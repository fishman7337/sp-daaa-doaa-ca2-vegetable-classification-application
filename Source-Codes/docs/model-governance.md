# Model Governance

This project uses a lightweight model registry under `models/` and TensorFlow Serving artifacts under `tf_models/`.

## Current Registry

| Model | Location | Purpose |
| --- | --- | --- |
| `model_a` | `models/model_a` | Local registry fixture for model-service tests and smoke checks. |
| `model_b` | `models/model_b` | Local registry fixture for model-service tests and smoke checks. |
| `vegnet-23` | `tf_models/vegnet-23` | TensorFlow Serving SavedModel artifact for VegNet 23x23 input. |
| `vegnet-101` | `tf_models/vegnet-101` | TensorFlow Serving SavedModel artifact for VegNet 101x101 input. |

## Required Metadata

Every package listed in `models/models.json` must include:

- `README.md`
- `labels.json`
- `config.json`
- optional model binary artifact

The registry validation script checks schema integrity and emits checksums:

```bash
python scripts/validate_model_registry.py --models-root models --report reports/model-registry-report.json
```

## Promotion Criteria

- Model files are reproducible from a notebook, training script, or documented export process.
- Labels and preprocessing config match the serving code.
- Validation, pytest, and smoke checks pass.
- Known limitations are documented.
- Rollback path is identified before deployment.

## Model Card Notes

For each promoted model, record:

- dataset source and split
- preprocessing steps
- metric summary
- known weak classes
- intended use
- out-of-scope use
- deployment endpoint
- rollback version
