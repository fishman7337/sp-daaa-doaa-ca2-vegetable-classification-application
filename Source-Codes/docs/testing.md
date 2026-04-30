# Testing Strategy

## Scope
The test suite is organized around four layers:

1. Unit tests (`@pytest.mark.unit`)
2. REST API tests (`@pytest.mark.api`)
3. Security tests (`@pytest.mark.security`)
4. End-to-end flow tests (`@pytest.mark.e2e`)
5. Documentation governance tests (`@pytest.mark.docs`)

All backend tests run against Flask + Jinja + SQLite test fixtures defined in
`backend/tests/conftest.py`.

## Part 3 Requirement Mapping

### 1) Unit testing categories
The repository covers more than 3 required categories:

- `validity`: input schema and payload validity
- `range`: boundary checks for numeric/query parameters
- `consistency`: deterministic behavior checks
- `expected_failure`: controlled negative-path failures
- `unexpected_failure`: resilience to malformed upstream behavior

Primary unit-focused module:
- `backend/tests/test_part3_unit_requirements.py`

### 2) REST APIs for crucial operations and predictions
Crucial APIs are implemented and tested, including:

- Auth: `/api/auth/*`
- Generic prediction/history: `/api/predict`, `/api/history*`
- Veggie prediction/history/catalog: `/api/veggie/*`
- Chatbot: `/api/chat/*`
- Health/models metadata: `/api/health`, `/api/models`

### 3) Testing all created REST APIs
REST coverage is provided by API-marked tests in:

- `backend/tests/test_auth.py`
- `backend/tests/test_predict.py`
- `backend/tests/test_history.py`
- `backend/tests/test_veggie_api.py`
- `backend/tests/test_chat.py`
- `backend/tests/test_models.py`
- `backend/tests/test_health.py`

## Security and E2E
- Security hardening + penetration-style tests:
  - `backend/tests/test_security_hardening.py`
  - `backend/tests/test_security_penetration.py`
- E2E multi-step system tests:
  - `backend/tests/test_e2e_flow.py`
  - `backend/tests/test_views_jinja.py`

## Run Commands
```bash
# Full backend + model service suite
pytest

# Targeted subsets
pytest -m unit
pytest -m api
pytest -m security
pytest -m e2e
pytest -m docs
pytest model_service/tests
```

## Coverage

CI enforces coverage thresholds for backend and model service jobs. The current default is 85 percent for each service.
