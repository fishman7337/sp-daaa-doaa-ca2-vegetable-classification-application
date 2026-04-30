# Security

This project is an academic MLOps application. It includes practical security controls, but it should not be treated as production-ready without additional review, monitoring, and infrastructure hardening.

## Supported Scope

Security guidance applies to:

- Flask backend routes and Jinja-rendered pages.
- Authentication, captcha, OTP, JWT, sessions, and profile flows.
- SQLite persistence and user-scoped data access.
- Upload handling for prediction images and avatars.
- Model-service and VegNet inference routing.
- CI/CD scans and dependency audits.

## Current Controls

- Bcrypt password hashing.
- JWT auth with role claims.
- Login rate limiting.
- Captcha and OTP flow support.
- Security headers including CSP, HSTS, frame protection, and content sniffing protection.
- User-scoped history and chat data access.
- No-store cache headers for sensitive routes.
- Query-token access limited to image retrieval routes.
- Pytest security and E2E suites.

## CI Security Gates

- `bandit` static analysis.
- `pip-audit` dependency audit.
- `gitleaks` secret scanning.
- Security-marked pytest suite.
- Docker build validation.

## Reporting

Do not create public issues containing secrets, exploit payloads, private data, or live credentials. Report concerns to the repository owner or the lecturer through the appropriate Singapore Polytechnic channel.

Include:

- affected route, file, or dependency
- reproduction steps
- expected versus actual behavior
- suggested mitigation, if known

## Secret Handling

- Never commit `.env`.
- Use `.env.example` only for placeholders.
- Configure production values in Render, GitHub/GitLab CI variables, or another secret manager.
- Rotate any exposed key immediately.

## Optional Integrations

`inference-sdk` is intentionally not part of the default backend install because Roboflow workflow mode is optional and that dependency chain may pin vulnerable transitive packages. Install it only in an isolated environment when workflow-based camera detection is required.
