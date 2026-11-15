"""Apply database migrations: the numbered .sql files in backend/migrations/.

Each file runs once per database. Applied files are recorded in the
schema_migrations table, so running this again only applies new files.

Run it by hand with:  python -m app.migrate
"""

import re
import sys
from pathlib import Path

from app import db
from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

_FILENAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")   # e.g. 001_create_users.sql
_LOCK_ID = 727_001  # any fixed number; every copy of the app uses the same one


def find_migrations(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """The migration files, in order. Rejects badly named or duplicate-numbered files."""
    files = sorted(directory.glob("*.sql"))
    for path in files:
        if not _FILENAME.match(path.name):
            raise ValueError(f"bad migration file name {path.name!r}; expected e.g. 001_create_users.sql")
    numbers = [path.name[:3] for path in files]
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        raise ValueError(f"two migrations share the number {', '.join(duplicates)}")
    return files


def apply_migrations(directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Run every migration not applied yet, in order. Returns the names applied now.

    Everything happens in ONE transaction: if any file fails, none of this
    run's changes are kept, and the database stays as it was.
    """
    migrations = find_migrations(directory)
    applied_now = []
    with db.get_connection() as conn:
        # If two copies of the app start at once, the second waits here
        # until the first is done, so no migration runs twice.
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_ID,))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename    text        PRIMARY KEY,
                applied_at  timestamptz NOT NULL DEFAULT now()
            )
        """)
        done = {row["filename"] for row in conn.execute("SELECT filename FROM schema_migrations")}
        for path in migrations:
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


def main() -> int:
    db.open_pool(get_settings())
    try:
        applied = apply_migrations()
    finally:
        db.close_pool()
    print("\n".join(f"applied {name}" for name in applied) or "database is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
