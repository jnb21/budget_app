"""Shared test setup. pytest loads this file automatically before the tests.

Tests that touch the database use a separate database, budget_test, in the
same Postgres container, so they can create and drop tables freely without
ever touching your real data in the budget database.
"""

from contextlib import contextmanager
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.rows import dict_row

from app import db
from app.config import Settings
from app.migrate import apply_migrations, ensure_app_login

TEST_DB_NAME = "budget_test"


def _to_test_database(url: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path=f"/{TEST_DB_NAME}"))


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings pointing at budget_test, created on first use if missing.

    Both logins from .env, pointed at budget_test: the app's restricted one
    (row-level security applies) and the owner (migrations, table setup).
    """
    dev = Settings()                                     # from .env: .../budget
    if not dev.migration_database_url:
        pytest.exit("set MIGRATION_DATABASE_URL in .env (see .env.example)")

    with psycopg.connect(dev.migration_database_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')

    settings = Settings(
        _env_file=None,
        database_url=_to_test_database(dev.database_url),
        migration_database_url=_to_test_database(dev.migration_database_url),
    )
    ensure_app_login(settings)  # the app's login must exist before any pool opens
    return settings


@pytest.fixture
def owner(test_settings):
    """Run SQL as the owner, who sees EVERY row (row-level security doesn't
    apply to owners). For setting up or checking what's really stored:

        with owner() as conn:
            conn.execute("SELECT count(*) FROM transactions")

    Checking with the app's login instead would see nothing without a user
    set, and a test like "no rows left" would pass even if nothing was deleted.
    """
    @contextmanager
    def connect():
        with psycopg.connect(test_settings.migration_database_url, row_factory=dict_row) as conn:
            yield conn  # committed at the end of the block
    return connect


@pytest.fixture
def db_pool(test_settings):
    """An open pool on budget_test for one test, closed afterwards."""
    db.close_pool()
    db.open_pool(test_settings)
    yield
    db.close_pool()


@pytest.fixture
def empty_database(db_pool, test_settings, owner):
    """budget_test with every table dropped, so each test starts from nothing."""
    database = urlsplit(test_settings.database_url).path.lstrip("/")
    assert database.endswith("_test"), f"refusing to wipe {database!r}: not a test database"
    with owner() as conn:  # only the owner may drop and create the schema
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


@pytest.fixture
def migrated(empty_database, test_settings):
    """budget_test with every real migration applied."""
    apply_migrations(test_settings)
