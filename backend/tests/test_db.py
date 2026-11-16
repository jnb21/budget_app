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


def test_work_is_rolled_back_when_an_error_happens(migrated, owner):
    # Act: add a user, then crash before the block ends.
    with pytest.raises(ZeroDivisionError):
        with db.get_connection() as conn:
            conn.execute("INSERT INTO users (email) VALUES ('rollback@example.com')")
            1 / 0

    # Assert: the user was never committed (checked as the owner, who sees every row).
    with owner() as conn:
        assert conn.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 0


def test_the_user_is_set_for_one_transaction_only(db_pool):
    with db.get_connection(user_id=42) as conn:
        during = conn.execute("SELECT current_setting('app.user_id', true) AS v").fetchone()["v"]
    with db.get_connection() as conn:  # the next borrower: likely the very same connection
        after = conn.execute("SELECT current_setting('app.user_id', true) AS v").fetchone()["v"]

    assert during == "42"
    assert after in (None, "")  # the next request must not act as user 42


def test_the_owner_login_is_refused(test_settings):
    # Owners skip row-level security without any error: refuse to start instead.
    owner_settings = Settings(_env_file=None, database_url=test_settings.migration_database_url)

    with pytest.raises(RuntimeError, match="skips row-level security"):
        db.open_pool(owner_settings)
    assert db._pool is None


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
