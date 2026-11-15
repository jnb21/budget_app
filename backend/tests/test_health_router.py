"""API tests for GET /health: fake HTTP requests, fake repository, no database.

TestClient sends requests straight to the app in memory (no server, no
network). dependency_overrides swaps get_health_service for one that uses a
fake repository, so we can test the "database down" response safely.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies import get_health_service
from app.routers import health
from app.services.health_service import HealthService
from tests.fakes import FakeHealthRepository


def client_with(repository: FakeHealthRepository) -> TestClient:
    """A tiny app with only the health router, wired to the given fake."""
    app = FastAPI()
    app.include_router(health.router)
    app.dependency_overrides[get_health_service] = lambda: HealthService(repository=repository)
    return TestClient(app)


def test_healthy_app_returns_200_and_ok():
    # Arrange
    client = client_with(FakeHealthRepository())

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_database_down_returns_503_and_degraded():
    client = client_with(FakeHealthRepository(error=ConnectionError("db is down")))

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_error_details_are_not_in_the_response():
    client = client_with(FakeHealthRepository(error=RuntimeError("password hunter2 rejected")))

    response = client.get("/health")

    assert "hunter2" not in response.text


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_only_get_is_allowed(method):
    client = client_with(FakeHealthRepository())

    response = getattr(client, method)("/health")

    assert response.status_code == 405  # Method Not Allowed
