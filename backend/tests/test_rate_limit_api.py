"""Full-stack tests for the rate limits: real HTTP requests, real database.

Each test's app gets a limiter with a fake clock, so the buckets don't
refill while a test runs (it would on a slow machine) and the counts are
exact. Every request from TestClient comes from the same address
("testclient"), like many users behind one office router.
"""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import create_app
from app.rate_limit import TokenBucketLimiter

PASSWORD = "correct horse battery"


@pytest.fixture
def client(empty_database, test_settings):
    db.close_pool()
    app = create_app(test_settings)
    app.state.limiter = TokenBucketLimiter(clock=lambda: 1000.0)  # time stands still
    with TestClient(app) as client:
        yield client


def sign_up(client, email):
    response = client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return dict(response.cookies)


def test_the_api_allows_100_requests_then_says_wait(client):
    sign_up(client, "alice@example.com")  # sign-up used 1 API token (counted by IP, no login yet)

    statuses = [client.get("/api/categories").status_code for _ in range(100)]
    refused = client.get("/api/categories")

    assert statuses == [200] * 100  # boundary: all 100 allowed
    assert refused.status_code == 429
    assert refused.headers["Retry-After"] == "1"
    assert "too many requests" in refused.json()["detail"]


def test_logged_in_users_on_the_same_ip_have_separate_buckets(client):
    bobs_cookies = sign_up(client, "bob@example.com")
    sign_up(client, "alice@example.com")  # the client now holds Alice's cookie
    for _ in range(100):
        client.get("/api/categories")
    assert client.get("/api/categories").status_code == 429  # Alice is out

    client.cookies.clear()
    client.cookies.update(bobs_cookies)
    assert client.get("/api/categories").status_code == 200  # Bob, same IP, isn't


def test_sign_up_allows_5_per_hour_from_one_ip(client):
    for n in range(5):
        sign_up(client, f"user{n}@example.com")

    sixth = client.post("/api/auth/signup", json={"email": "user5@example.com", "password": PASSWORD})

    assert sixth.status_code == 429
    assert int(sixth.headers["Retry-After"]) == 12 * 60  # one sign-up token every 12 minutes


def test_login_allows_20_tries_per_ip_even_with_different_emails(client):
    """The 5-per-email limit doesn't catch someone trying one password on
    many emails; this one does."""
    tries = [client.post("/api/auth/login", json={"email": f"user{n}@example.com", "password": PASSWORD})
             for n in range(20)]
    blocked = client.post("/api/auth/login", json={"email": "user20@example.com", "password": PASSWORD})

    assert {r.status_code for r in tries} == {401}  # wrong, but allowed to try
    assert blocked.status_code == 429


def test_deleting_the_account_allows_5_password_tries(client):
    sign_up(client, "alice@example.com")
    for _ in range(5):
        wrong = client.post("/api/account/delete", json={"password": "not the password"})
        assert wrong.status_code == 422

    sixth = client.post("/api/account/delete", json={"password": PASSWORD})  # even the right one

    assert sixth.status_code == 429


def test_health_is_not_limited(client):
    statuses = {client.get("/health").status_code for _ in range(150)}

    assert statuses == {200}
