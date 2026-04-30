# Model Serving

TensorFlow Serving support files and model-training evidence.

## Responsibilities

- Keep serving configuration for exported VegNet models.
- Store notebooks and rendered notebook evidence.
- Provide a Dockerfile for TensorFlow Serving-style deployment when needed.

## Structure

- `notebooks/`: training/export notebooks and documentation.
- `notebooks/exports/`: rendered notebook evidence.
- `tf_models/`: legacy serving mount placeholder.
- `models.config`: TensorFlow Serving model configuration.
- `Dockerfile`: container definition for serving exported models.

The lightweight Flask `model_service/` is used for local CI smoke checks; this folder captures the TensorFlow Serving side of the project.
