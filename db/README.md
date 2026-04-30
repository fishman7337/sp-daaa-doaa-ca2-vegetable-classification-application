# Database

SQLite database schema and initialization helpers.

## Files

- `schema.sql`: application schema for users, predictions, chat, vegetables, captcha, and OTP flows.
- `init_db.py`: helper for initializing the database from the schema.
- `app.db`: local runtime database, ignored for source-control purposes.

Use `DATABASE_PATH` to point the backend at a different SQLite file.
