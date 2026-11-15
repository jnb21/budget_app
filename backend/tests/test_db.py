"""Integration tests for db.py: these talk to the real Postgres container
(the budget_test database, see conftest.py).

Start it first with `docker compose up -d` from the repo root.
"""

from urllib.parse import urlsplit, urlunsplit

import pytest
from psycopg_pool import PoolTimeout

from app import db
from app.config import Settings


@pytest.fixture(autouse=True)
def closed_pool_after_each_test():
    """Every test starts and ends with no pool open, so tests can't affect each other."""
    db.close_pool()
    yield
    db.close_pool()


def test_can_run_a_query(db_pool):
    with db.get_connection() as conn:
        row = conn.execute("SELECT 1 AS answer").fetchone()

    assert row == {"answer": 1}  # a dict, thanks to row_factory=dict_row


def test_work_is_rolled_back_when_an_error_happens(empty_database):
    # Arrange + Act: create a table, then crash before the block ends.
    with pytest.raises(ZeroDivisionError):
        with db.get_connection() as conn:
            conn.execute("CREATE TABLE rollback_probe (id int)")
            1 / 0

    # Assert: the table was never committed.
    with db.get_connection() as conn:
        row = conn.execute("SELECT to_regclass('rollback_probe') AS found").fetchone()
    assert row["found"] is None


def test_using_the_pool_before_opening_it_is_an_error():
    with pytest.raises(RuntimeError, match="not open"):
        with db.get_connection():
            pass


def test_wrong_password_fails_at_startup(test_settings):
    # Arrange: the test URL with the password swapped for a wrong one.
    real = urlsplit(test_settings.database_url)
    bad_netloc = f"{real.username}:wrong-password@{real.hostname}:{real.port}"
    bad_settings = Settings(
        _env_file=None,
        database_url=urlunsplit(real._replace(netloc=bad_netloc)),
        db_connect_timeout=2,  # don't wait the default 10 s in a test
    )

    # Act + Assert
    with pytest.raises(PoolTimeout):
        db.open_pool(bad_settings)
    assert db._pool is None  # a failed start leaves nothing half-open
