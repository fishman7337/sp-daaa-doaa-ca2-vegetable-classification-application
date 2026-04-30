# API Contract

This document defines the intended REST APIs for the web app and model serving service.
Details will be finalized during implementation.

## Web app API
- GET /health
- GET /login
- POST /login
- GET /predict
- POST /predict
- GET /history

## Model serving API
- GET /health
- GET /models
- POST /predict

## Request and response (placeholder)
- Request fields: `model`, `inputs`, optional `metadata`
- Response fields: `model`, `outputs`, optional `metrics` and `latency_ms`