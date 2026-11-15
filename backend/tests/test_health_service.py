"""Unit tests for HealthService: no database at all.

The service gets a fake repository: a tiny class with a ping() method that
we control. That lets us test "what if the database is down?" in a few
milliseconds, without stopping Postgres.
"""

import logging

from app.services.health_service import HealthService, HealthStatus
from tests.fakes import FakeHealthRepository as FakeRepository


def test_status_is_ok_when_the_database_answers():
    # Arrange
    service = HealthService(repository=FakeRepository())

    # Act
    status = service.check()

    # Assert
    assert status == HealthStatus(status="ok", database="ok")


def test_status_is_degraded_when_the_database_fails():
    service = HealthService(repository=FakeRepository(error=ConnectionError("db is down")))

    status = service.check()

    assert status == HealthStatus(status="degraded", database="unavailable")


def test_the_database_is_asked_exactly_once():
    repository = FakeRepository()

    HealthService(repository=repository).check()

    assert repository.calls == 1


def test_the_failure_is_written_to_the_log(caplog):
    service = HealthService(repository=FakeRepository(error=ConnectionError("db is down")))

    with caplog.at_level(logging.ERROR):
        service.check()

    assert "database did not answer" in caplog.text
    assert "db is down" in caplog.text  # the real cause is in the log for developers


def test_error_details_never_reach_the_status():
    secret_detail = "connection to budget:hunter2@10.0.0.5 failed"
    service = HealthService(repository=FakeRepository(error=RuntimeError(secret_detail)))

    status = service.check()

    assert secret_detail not in str(status)
    assert "hunter2" not in str(status)
