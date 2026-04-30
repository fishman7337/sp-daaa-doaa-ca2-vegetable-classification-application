# Development Guide

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
pip install -r model_service/requirements-dev.txt
copy .env.example .env
```

Edit `.env` before running the app. Do not commit real secrets.

## Run Services

```bash
python main.py
```

Backend and web UI run on `http://localhost:5000`; the local model service runs on `http://localhost:8000`.

## Quality Checks

```bash
ruff check backend main.py
ruff check model_service
ruff format --check backend main.py
ruff format --check model_service
python scripts/check_readmes.py
pytest
```

## Change Checklist

- Keep changes scoped to one concern.
- Update tests when behavior changes.
- Update docs when commands, configuration, routes, or operations change.
- Run the relevant pytest subset before handing over.
- Never commit `.env`, local databases, upload files, or generated cache folders.
