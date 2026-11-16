"""Apply database migrations: the numbered .sql files in backend/migrations/.

Each file runs once per database. Applied files are recorded in the
schema_migrations table, so running this again only applies new files.

Migrations run as the OWNER (MIGRATION_DATABASE_URL), never as the app's
own login: only the owner may create tables and rules.

Run it by hand with:  python -m app.migrate
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.config import Settings, get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

_FILENAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")   # e.g. 001_create_users.sql
_LOCK_ID = 727_001  # any fixed number; every copy of the app uses the same one
APP_GROUP_ROLE = "budget_rw"  # may read and write rows; the app's login is a member


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


def ensure_app_login(settings: Settings) -> None:
    """Create the app's login from DATABASE_URL (or set its password if it
    exists) and make it a member of budget_rw. Run as the owner.

    So the password lives in one place, the .env file: change it there and
    the next migration run updates Postgres to match.
    """
    if not settings.migration_database_url:
        raise RuntimeError("MIGRATION_DATABASE_URL is not set: migrations need the owner login")
    app_url, owner_url = urlsplit(settings.database_url), urlsplit(settings.migration_database_url)
    user, password = unquote(app_url.username or ""), unquote(app_url.password or "")
    if not user or not password:
        raise ValueError("DATABASE_URL needs a user and a password")
    if user == unquote(owner_url.username or ""):
        raise ValueError("DATABASE_URL must not use the owner's login: owners skip row-level security")

    # autocommit: each statement stands alone, so "already exists" doesn't undo the rest.
    with psycopg.connect(settings.migration_database_url, autocommit=True) as conn:
        superuser = conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname = %s", (user,)).fetchone()
        if superuser and superuser[0]:
            raise ValueError(f"DATABASE_URL's login {user!r} is a superuser: superusers skip row-level security")
        for name, create in ((APP_GROUP_ROLE, "CREATE ROLE {} NOLOGIN"), (user, "CREATE ROLE {} LOGIN")):
            try:
                conn.execute(sql.SQL(create).format(sql.Identifier(name)))
            except psycopg.errors.DuplicateObject:
                pass  # created earlier (roles are shared by every database on the server)
        conn.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(user), sql.Literal(password)))
        conn.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(APP_GROUP_ROLE), sql.Identifier(user)))


def apply_migrations(settings: Settings, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Run every migration not applied yet, in order. Returns the names applied now.

    Everything happens in ONE transaction: if any file fails, none of this
    run's changes are kept, and the database stays as it was.
    """
    migrations = find_migrations(directory)
    ensure_app_login(settings)
    applied_now = []
    # The with-block commits at the end, or rolls everything back on an error.
    with psycopg.connect(settings.migration_database_url, row_factory=dict_row) as conn:
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
    applied = apply_migrations(get_settings())
    print("\n".join(f"applied {name}" for name in applied) or "database is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
