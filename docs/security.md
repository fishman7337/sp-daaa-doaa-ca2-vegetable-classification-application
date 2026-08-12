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

## Dependency Audit Policy

- Runtime and development manifests must pass `pip-audit` without blanket
  advisory suppressions. Each development manifest includes its corresponding
  runtime manifest, so CI audits the complete resolved service environment.
- The Pillow lower bound is `12.3.0`, the first release that clears all Pillow
  advisories known to the audit database at the 2026-08-11 review.
- `aiohttp` is not a backend or model-service dependency. Its obsolete CI
  suppressions were removed instead of adding an unnecessary constraint.
- pytest is constrained to `9.0.3` or newer to remediate `PYSEC-2026-1845` in
  the backend and model-service test environments.
- Any future exception must identify one advisory and package, explain why an
  upgrade is incompatible, name an owner, link a remediation issue, and include
  a review date no more than 90 days away. Expired exceptions fail review.

Current exceptions: **none**.

The 2026-08-11 review reproduced the removed exceptions against historical
versions: `CVE-2026-25990` affected Pillow 12.1.0, while `CVE-2025-53643` and
`CVE-2025-69223` through `CVE-2025-69230` affected aiohttp 3.12.13. The current
runtime manifests resolve neither vulnerable version.

## Optional Integrations

Roboflow workflow detection requires `inference-sdk`. Keep it out of default production dependencies unless workflow mode is actively used and its transitive dependencies have been reviewed.
