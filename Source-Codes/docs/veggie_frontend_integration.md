# VeggieAI Frontend Integration Notes

The Flask backend now exposes VeggieAI-compatible APIs using SQLite persistence.

## Auth
- `POST /api/auth/signup`
  - body: `{ "name": "Alice", "email": "alice@example.com", "password": "secret123" }`
- `POST /api/auth/login`
  - body: `{ "email": "alice@example.com", "password": "secret123" }`
  - also supports legacy `{ "username": "...", "password": "..." }`
- `GET /api/auth/me`
- `POST /api/auth/logout`

All auth responses include:
- `token`
- `user: { id, username, name, email, role, avatar }`

## Catalog + Prices
- `GET /api/veggie/catalog`
- `GET /api/veggie/prices`
- `GET /api/veggie/prices?vegetable=tomato`

Each vegetable item includes:
- `name`, `scientificName`, `category`, `description`, `nutrients`
- `prices` and `priceDetails`
- `unit`, `seasonality`, `storageLife`

## Prediction + History
- `POST /api/veggie/predict` (JWT required)
  - multipart: `image`
- `GET /api/veggie/history` (JWT required)
- `GET /api/veggie/history/<id>` (JWT required)
- `GET /api/veggie/history/<id>/image` (JWT required)
- `DELETE /api/veggie/history/<id>` (JWT required)
- `DELETE /api/veggie/history` (JWT required)

Returned prediction shape:
- `id`
- `image` (URL)
- `vegetable`
- `scientificName`
- `category`
- `confidence`
- `timestamp`
- `prices`
