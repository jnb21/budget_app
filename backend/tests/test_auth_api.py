"""Full-stack tests for login, sessions, the account, and category changes:
real HTTP with real cookies -> routers -> services -> Postgres (budget_test).
Nothing is overridden here: the session cookie decides who you are.
"""

import hashlib

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import create_app
from app.services.auth_service import MAX_FAILURES

PASSWORD = "correct horse battery"
TRANSACTION = {"posted_date": "2026-11-03", "amount_cents": -4_599, "description": "Metro"}


@pytest.fixture
def client(empty_database, test_settings):
    db.close_pool()
    with TestClient(create_app(test_settings)) as client:  # keeps cookies between requests
        yield client


def sign_up(client, email):
    response = client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response


def log_in(client, email, password=PASSWORD):
    client.cookies.clear()
    return client.post("/api/auth/login", json={"email": email, "password": password})


def category_id(client, name):
    return next(c["id"] for c in client.get("/api/categories").json() if c["name"] == name)


# --- Without logging in ---------------------------------------------------------

@pytest.mark.parametrize("method, url", [
    ("GET", "/api/dashboard?month=2026-11"),
    ("GET", "/api/transactions?month=2026-11"),
    ("POST", "/api/transactions"),
    ("GET", "/api/budgets?month=2026-11"),
    ("GET", "/api/categories"),
    ("GET", "/api/auth/me"),
    ("GET", "/api/account/export"),
    ("POST", "/api/account/delete"),
])
def test_user_data_needs_a_login(client, method, url):
    response = client.request(method, url, json=TRANSACTION if method == "POST" else None)

    assert response.status_code == 401
    assert response.json() == {"detail": "please log in"}


def test_health_stays_public(client):
    assert client.get("/health").status_code == 200


# --- Sign up, the cookie, log out -----------------------------------------------

def test_sign_up_sets_a_safe_session_cookie(client):
    response = sign_up(client, "alice@example.com")

    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith("session=")
    assert "httponly" in cookie          # JavaScript can't read it
    assert "samesite=lax" in cookie      # other sites can't use it for POST/PUT/DELETE
    assert "path=/" in cookie
    assert client.get("/api/auth/me").json()["email"] == "alice@example.com"


def test_the_database_never_sees_the_raw_token(client):
    sign_up(client, "alice@example.com")
    token = client.cookies["session"]

    with db.get_connection() as conn:
        stored = conn.execute("SELECT token_hash FROM sessions").fetchone()["token_hash"]

    assert stored != token
    assert stored == hashlib.sha256(token.encode()).hexdigest()


def test_signing_up_twice_with_the_same_email_is_refused(client):
    sign_up(client, "alice@example.com")

    response = client.post("/api/auth/signup", json={"email": "Alice@Example.com", "password": PASSWORD})

    assert response.status_code == 409


def test_a_short_password_is_refused(client):
    response = client.post("/api/auth/signup", json={"email": "alice@example.com", "password": "short"})

    assert response.status_code == 422


def test_after_logging_out_the_old_cookie_is_useless(client):
    sign_up(client, "alice@example.com")
    old_token = client.cookies["session"]

    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set("session", old_token)  # an attacker who copied the cookie earlier

    assert client.get("/api/auth/me").status_code == 401


# --- Log in ----------------------------------------------------------------------

def test_wrong_password_and_unknown_email_look_the_same(client):
    sign_up(client, "alice@example.com")

    wrong_password = log_in(client, "alice@example.com", "not the password")
    unknown_email = log_in(client, "nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": "wrong email or password"}


def test_too_many_wrong_passwords_lock_the_login_for_a_while(client):
    sign_up(client, "alice@example.com")
    for _ in range(MAX_FAILURES):
        assert log_in(client, "alice@example.com", "guess").status_code == 401

    blocked = log_in(client, "alice@example.com")  # even with the right password

    assert blocked.status_code == 429


def test_the_demo_user_can_log_in_after_seeding(client):
    from datetime import date

    from app.seed import DEMO_PASSWORD, seed_demo_data
    seed_demo_data(date(2026, 11, 15))

    response = log_in(client, "demo@budget.local", DEMO_PASSWORD)

    assert response.status_code == 200
    assert len(client.get("/api/transactions", params={"month": "2026-11"}).json()) > 0


# --- Isolation with real logins ---------------------------------------------------

def test_bob_logged_in_cannot_see_alices_data(client):
    sign_up(client, "bob@example.com")
    client.cookies.clear()
    sign_up(client, "alice@example.com")
    client.post("/api/transactions", json=TRANSACTION)

    log_in(client, "bob@example.com")

    assert client.get("/api/transactions", params={"month": "2026-11"}).json() == []
    assert client.get("/api/account/export").json()["transactions"] == []


# --- The account: export and delete ------------------------------------------------

def test_export_contains_my_data(client):
    sign_up(client, "alice@example.com")
    client.post("/api/transactions", json=TRANSACTION)
    client.post("/api/categories", json={"name": "Pets"})

    export = client.get("/api/account/export").json()

    assert export["account"]["email"] == "alice@example.com"
    assert [t["description"] for t in export["transactions"]] == ["Metro"]
    assert [c["name"] for c in export["categories"]] == ["Pets"]
    assert "password_hash" not in str(export)


def test_deleting_the_account_removes_everything(client):
    sign_up(client, "alice@example.com")
    client.post("/api/transactions", json=TRANSACTION)

    wrong = client.post("/api/account/delete", json={"password": "not the password"})
    assert wrong.status_code == 422

    right = client.post("/api/account/delete", json={"password": PASSWORD})
    assert right.status_code == 204
    with db.get_connection() as conn:
        left = conn.execute("SELECT (SELECT count(*) FROM users) + (SELECT count(*) FROM transactions)"
                            " + (SELECT count(*) FROM sessions) AS n").fetchone()["n"]
    assert left == 0
    assert log_in(client, "alice@example.com").status_code == 401


# --- Categories: rename and delete -------------------------------------------------

def test_renaming_my_category(client):
    sign_up(client, "alice@example.com")
    pets = client.post("/api/categories", json={"name": "Pets"}).json()

    renamed = client.put(f"/api/categories/{pets['id']}", json={"name": "Pet care"})

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Pet care"


def test_renaming_to_an_existing_name_is_a_conflict(client):
    sign_up(client, "alice@example.com")
    pets = client.post("/api/categories", json={"name": "Pets"}).json()

    assert client.put(f"/api/categories/{pets['id']}", json={"name": "groceries"}).status_code == 409
    assert client.put(f"/api/categories/{pets['id']}", json={"name": "PETS"}).status_code == 200  # its own name


def test_default_categories_cannot_be_changed(client):
    sign_up(client, "alice@example.com")
    groceries = category_id(client, "Groceries")

    assert client.put(f"/api/categories/{groceries}", json={"name": "Food"}).status_code == 422
    assert client.delete(f"/api/categories/{groceries}").status_code == 422


def test_deleting_a_category_uncategorizes_its_transactions_and_drops_its_budgets(client):
    sign_up(client, "alice@example.com")
    pets = client.post("/api/categories", json={"name": "Pets"}).json()
    client.post("/api/transactions", json={**TRANSACTION, "category_id": pets["id"]})
    client.put("/api/budgets", json={"category_id": pets["id"], "month": "2026-11", "limit_cents": 10_000})

    assert client.delete(f"/api/categories/{pets['id']}").status_code == 204

    transaction = client.get("/api/transactions", params={"month": "2026-11"}).json()[0]
    assert (transaction["category_id"], transaction["category_source"]) == (None, "none")
    assert client.get("/api/budgets", params={"month": "2026-11"}).json() == []


def test_bob_cannot_rename_or_delete_alices_category(client):
    sign_up(client, "alice@example.com")
    pets = client.post("/api/categories", json={"name": "Pets"}).json()
    client.cookies.clear()
    sign_up(client, "bob@example.com")

    assert client.put(f"/api/categories/{pets['id']}", json={"name": "Mine now"}).status_code == 404
    assert client.delete(f"/api/categories/{pets['id']}").status_code == 404


def test_an_expired_session_is_refused_by_the_database(client):
    sign_up(client, "alice@example.com")
    with db.get_connection() as conn:  # pretend 31 days went by
        conn.execute("UPDATE sessions SET expires_at = now() - interval '1 second'")

    assert client.get("/api/auth/me").status_code == 401
