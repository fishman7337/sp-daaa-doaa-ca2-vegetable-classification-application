# Web App

The web app contains Jinja templates and static assets rendered by the backend Flask service.

## Responsibilities

- Public home and auth pages.
- Authenticated prediction, history, prices, and profile views.
- Browser-side JavaScript for API calls, uploads, camera detection, theme behavior, and UI state.
- Static CSS, image, audio, and asset files.

## Structure

- `app/templates/`: Jinja page templates.
- `app/static/`: CSS, JS, images, audio, and bundled assets.
- `app/core/` and `app/services/`: reserved compatibility modules.
- `tests/`: reserved for frontend-specific tests.

The deployed runtime is the backend container. This folder is copied into the backend image and mounted by `backend/app.py`.
