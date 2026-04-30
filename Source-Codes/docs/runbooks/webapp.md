# Web App Runbook

## Responsibilities
- Handle login and session management.
- Collect input and call model serving.
- Store prediction history and support search.

## Configuration
- `SERVING_BASE_URL`
- `WEBAPP_SECRET_KEY`

## Deployment checklist
- Build image
- Verify login
- Verify prediction workflow
- Verify history search and filter