# Backend Tests

This folder contains pytest coverage for backend behavior.

## Coverage Areas

- API contract and response envelopes.
- Authentication, captcha, OTP, JWT, and session behavior.
- Prediction, history, chat, profile, and vegetable routes.
- Security hardening and penetration-style negative tests.
- Jinja route rendering and smoke-script behavior.
- Documentation structure governance.

Run:

```bash
pytest backend/tests
pytest -m security backend/tests
pytest -m e2e backend/tests
```
