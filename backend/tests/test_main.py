"""Full-stack tests: nothing is fake.

A real HTTP request goes through the real router, service and repository to
the real Postgres (budget_test). Using TestClient in a `with` block also runs
the app's startup (open the pool, apply migrations) and shutdown (close it).
"""

from urllib.parse import urlsplit, urlunsplit

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import PoolTimeout

from app import db
from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(empty_database, test_settings):
    db.close_pool()  # let the app's own startup open the pool
    with TestClient(create_app(test_settings)) as client:
        yield client


def table_exists(name):
    with db.get_connection() as conn:
        return conn.execute("SELECT to_regclass(%s) AS found", (name,)).fetchone()["found"] is not None


def test_health_works_through_every_layer(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_startup_applies_the_migrations(client):
    # The database was emptied before the app started; startup created the tables.
    assert table_exists("users")
    assert table_exists("schema_migrations")


def test_shutdown_closes_the_pool(empty_database, test_settings):
    db.close_pool()
    with TestClient(create_app(test_settings)):
        assert db._pool is not None   # open while the app runs

    assert db._pool is None           # closed once it stops


def test_app_refuses_to_start_when_the_database_is_unreachable(test_settings):
    db.close_pool()
    real = urlsplit(test_settings.database_url)
    unreachable = urlunsplit(real._replace(netloc=f"{real.username}:x@127.0.0.1:1"))  # nothing on port 1
    bad_settings = Settings(_env_file=None, database_url=unreachable, db_connect_timeout=1)

    with pytest.raises(PoolTimeout):
        with TestClient(create_app(bad_settings)):
            pass  # never reached: startup fails first

    assert db._pool is None


def test_pool_timeout_during_a_request_becomes_503(client):
    # Arrange: a route that fails the way an exhausted or lost pool does.
    @client.app.get("/needs-database")
    def needs_database():
        raise PoolTimeout("no connection available")

    # Act
    response = client.get("/needs-database")

    # Assert
    assert response.status_code == 503
    assert response.json() == {"detail": "Database temporarily unavailable, please try again shortly."}
