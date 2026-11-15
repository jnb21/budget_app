"""Shared test setup. pytest loads this file automatically before the tests.

Tests that touch the database use a separate database, budget_test, in the
same Postgres container, so they can create and drop tables freely without
ever touching your real data in the budget database.
"""

from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from app import db
from app.config import Settings

TEST_DB_NAME = "budget_test"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings pointing at budget_test, created on first use if missing."""
    dev_url = Settings().database_url                    # from .env: .../budget
    parts = urlsplit(dev_url)
    test_url = urlunsplit(parts._replace(path=f"/{TEST_DB_NAME}"))

    with psycopg.connect(dev_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')

    return Settings(_env_file=None, database_url=test_url)


@pytest.fixture
def db_pool(test_settings):
    """An open pool on budget_test for one test, closed afterwards."""
    db.close_pool()
    db.open_pool(test_settings)
    yield
    db.close_pool()


@pytest.fixture
def empty_database(db_pool, test_settings):
    """budget_test with every table dropped, so each test starts from nothing."""
    database = urlsplit(test_settings.database_url).path.lstrip("/")
    assert database.endswith("_test"), f"refusing to wipe {database!r}: not a test database"
    with db.get_connection() as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
