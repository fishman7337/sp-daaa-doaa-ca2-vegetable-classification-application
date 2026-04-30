# Backend Utilities

Shared backend helpers live here.

## Modules

- `files.py`: safe uploaded-file path resolution.
- `jwt.py`: JWT creation and route guards.
- `logging.py`: structured log helper.
- `mailer.py`: SMTP delivery helper.
- `models_config.py`: model registry readers for the backend.
- `rate_limiter.py`: login and OTP rate limiting.
- `responses.py`: consistent API response envelopes.
- `search.py`: search query construction.
- `security.py`: password hashing and admin seeding.
- `validation.py`: request and image validation.

Utilities should stay framework-light and covered by tests where behavior is non-trivial.
