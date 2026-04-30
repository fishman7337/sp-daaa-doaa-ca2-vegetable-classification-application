"""CLI helper to initialize the SQLite database schema."""

import argparse
import sqlite3
from pathlib import Path


def init_db(db_path: str, schema_path: str) -> None:
    """Create or reset a SQLite database from a schema SQL file."""
    path = Path(db_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    with open(schema_path, "r", encoding="utf-8") as handle:
        conn.executescript(handle.read())
    conn.commit()
    conn.close()


def main() -> None:
    """Parse CLI flags and initialize the SQLite database."""
    parser = argparse.ArgumentParser(description="Initialize SQLite database")
    parser.add_argument("--db", default="db/app.db", help="Path to SQLite DB")
    parser.add_argument("--schema", default="db/schema.sql", help="Path to schema.sql")
    args = parser.parse_args()
    init_db(args.db, args.schema)
    print(f"Initialized database at {args.db}")


if __name__ == "__main__":
    main()
