"""Integration tests for HealthRepository: real Postgres (budget_test).

A repository is tested against the real database, never a fake one:
the SQL is exactly what we want to check.
"""

import pytest

from app import db
from app.repositories.health_repository import HealthRepository


def test_ping_succeeds_when_the_database_answers(db_pool):
    # Arrange
    repository = HealthRepository()

    # Act + Assert: no exception means the database answered.
    repository.ping()


def test_ping_raises_when_there_is_no_database_connection():
    # Arrange: make sure no pool is open.
    db.close_pool()
    repository = HealthRepository()

    # Act + Assert: the error comes out unchanged, for the service to handle.
    with pytest.raises(RuntimeError, match="not open"):
        repository.ping()
