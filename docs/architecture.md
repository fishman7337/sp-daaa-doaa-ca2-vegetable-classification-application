# Architecture

This document describes the application architecture for the VeggieAI MLOps Platform.

## System Diagram
```text
+-----------------------------+
| Flask + Jinja Web UI        |
| (/, /auth, /predict, ...)   |
+--------------+--------------+
               |
               | same-process API calls
               v
+-----------------------------+        HTTP        +-----------------------+
| Backend Flask API           | -----------------> | Model Service Flask   |
| auth, history, chat, prices |                    | vegnet inference      |
+--------------+--------------+                    +-----------------------+
               |
               v
        +--------------+
        | SQLite DB    |
        | user-scoped  |
        | app data     |
        +--------------+
```

## Services
- **Frontend (`webapp/app/`)**: Jinja templates and static assets (JavaScript, CSS, images, audio) rendered by Flask.
- **Backend (`backend/`)**: Flask API/service layer handling auth, captcha/OTP, profile, chat, prediction history, pricing data, and view routing.
- **Model Service (`model_service/`)**: isolated local inference service used by `/api/predict`, registry validation, and runtime smoke checks.
- **TensorFlow Serving Assets (`tf_models/`, `model_serving/`)**: exported SavedModel assets and serving configuration for VegNet-style deployment.
- **Database (`db/`)**: SQLite schema/init scripts.
- **Models (`models/`)**: model metadata and selection config.

## Security Design
- Passwords are hashed with salt before persistence.
- JWT secures API routes; session bridge secures Jinja routes.
- Public pages: `/`, `/auth`.
- Protected pages: `/predict`, `/prices`, `/profile`, `/history`.
- Captcha + OTP enforced through backend auth flow.
- Security headers, CSP, HTTPS redirect controls via env configuration.

## Data Ownership
- Prediction history is stored per `user_id`.
- Chat history is stored per `user_id`.
- Uploaded assets and avatar data are linked to authenticated users.

## Inference Routing
- `/api/predict` calls `MODEL_SERVICE_URL`, which defaults to the local model service during development.
- `/api/veggie/predict` calls configured TensorFlow Serving endpoints for `vegnet-23` and `vegnet-101`.
- `VEGNET_REMOTE_ENABLED=false` disables the remote VegNet path when external model services are unavailable.
- Camera detection uses Roboflow only when `ROBOFLOW_API_KEY` and a hosted model or workflow ID are configured.
