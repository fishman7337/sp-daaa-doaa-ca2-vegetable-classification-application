# Security

## Authentication and Session Controls
- JWT tokens are issued by backend auth endpoints and required for protected APIs.
- Flask session bridge (`/web/session/login`) is used for Jinja page access.
- Protected pages redirect unauthenticated users to `/auth`.
- OTP flow is supported for login/signup verification.
- Captcha challenge is supported before auth submission.

## Credential Storage
- Passwords are stored as salted bcrypt hashes.
- Plaintext passwords are never persisted.

## Authorization
- Prediction, history, profile, and chat data are user-scoped by `user_id`.
- Cross-user history/image access is denied by backend checks.

## Transport and Header Hardening
- Configurable HTTPS enforcement (`FORCE_HTTPS`).
- Security headers are applied (`HSTS`, `CSP`, `X-Frame-Options`, `X-Content-Type-Options`, etc.).
- Authenticated responses use `Cache-Control: no-store`.

## Input and Upload Hardening
- Validation schemas on auth and API payloads.
- Image uploads validated and size-limited.
- SQL access is parameterized to reduce injection risk.

## Automated Security Testing
- `pytest -m security backend/tests`
- `pytest -m e2e backend/tests`
- Includes SQL injection attempts, JWT tampering, IDOR, brute-force/OTP abuse, malformed uploads, and header/cookie checks.

## CI Security Gates
- Bandit SAST
- pip-audit (Python dependencies)
- gitleaks (secret scanning)

## Optional Integrations

Roboflow workflow detection requires `inference-sdk`. Keep it out of default production dependencies unless workflow mode is actively used and its transitive dependencies have been reviewed.
