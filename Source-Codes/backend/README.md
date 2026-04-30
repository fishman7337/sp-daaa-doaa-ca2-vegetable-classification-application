# Backend

The backend is a Flask application that serves the JSON API and renders the Jinja web UI through `webapp/app`.

## Responsibilities

- Authentication, captcha, OTP, JWT, and session handling.
- User profile, chat, vegetable catalog, price, prediction, and history APIs.
- SQLite persistence through repository helpers.
- Security headers, CORS, HTTPS redirect controls, and request IDs.
- Calls to the local model service and configured VegNet endpoints.

## Key Files

- `app.py`: Flask application factory and route registration.
- `config.py`: environment-driven settings.
- `auth.py`, `predict.py`, `veggie.py`, `chat.py`, `history.py`: route modules.
- `repository.py`: database read/write layer.
- `utils/`: shared security, validation, response, logging, JWT, and file helpers.
- `tests/`: backend pytest suite.

## Local Commands

```bash
pip install -r backend/requirements-dev.txt
pytest backend/tests
```
