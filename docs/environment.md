# Environment Reference

Use `.env.example` as the baseline for local development. Real secrets belong in `.env` locally and in the deployment platform for hosted environments.

## Core Backend

- `SECRET_KEY`: Flask session signing secret.
- `JWT_SECRET`: JWT signing secret.
- `JWT_EXPIRES_MINUTES`: token lifetime.
- `DATABASE_PATH`: SQLite database path.
- `UPLOAD_DIR`: uploaded prediction images and avatars.
- `MODELS_ROOT`: model registry root.
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`: initial seeded admin account.

## Model Routing

- `MODEL_SERVICE_URL`: local model-service URL used by `/api/predict`.
- `MODEL_SERVICE_TIMEOUT_SEC`: backend request timeout for model-service calls.
- `VEGGIE_DEFAULT_MODEL`: default UI VegNet model.
- `VEGNET_REMOTE_ENABLED`: enables remote VegNet inference for `/api/veggie/predict`.
- `VEGNET_23_URL`, `VEGNET_101_URL`: TensorFlow Serving model endpoints.
- `VEGNET_23_RESAMPLE`, `VEGNET_101_RESAMPLE`: image resize strategies.

## Optional Integrations

- `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, `OPENAI_TIMEOUT_SEC`: chatbot integration.
- `ROBOFLOW_API_KEY`, `ROBOFLOW_MODEL_ID`: hosted Roboflow detection.
- `ROBOFLOW_WORKSPACE`, `ROBOFLOW_WORKFLOW_ID`: workflow-based Roboflow detection.
- `SMTP_*`: email transport for OTP/password reset flows.

## Security

- `CAPTCHA_*`: captcha behavior and development mode.
- `OTP_*`: OTP behavior and development mode.
- `SECURITY_HEADERS_ENABLED`: toggles default security headers.
- `FORCE_HTTPS`: redirects HTTP requests when running behind HTTPS.
- `SESSION_COOKIE_*`: session cookie protection settings.
- `CSP_POLICY`, `PERMISSIONS_POLICY`: browser security policies.
