"""Full-stack API tests: real HTTP requests -> routers -> services ->
repositories -> Postgres (budget_test). Nothing is fake except WHO is logged
in: get_current_user_id is overridden so each test can act as Alice or Bob.

The most important tests here are the isolation ones: Bob must never see or
change Alice's data, whatever he tries.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import db
from app.dependencies import get_current_user_id
from app.main import create_app


class Users:
    """Creates users and switches who the app thinks is logged in."""

    def __init__(self):
        self.current = None

    def create(self, email):
        with db.get_connection() as conn:
            return conn.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (email,)).fetchone()["id"]


@pytest.fixture
def users():
    return Users()


@pytest.fixture
def client(empty_database, test_settings, users):
    db.close_pool()
    app = create_app(test_settings)
    app.dependency_overrides[get_current_user_id] = lambda: users.current
    with TestClient(app) as client:  # startup runs the migrations
        users.alice = users.create("alice@example.com")
        users.bob = users.create("bob@example.com")
        users.current = users.alice
        yield client


def category_id(client, name):
    return next(c["id"] for c in client.get("/api/categories").json() if c["name"] == name)


def add(client, **fields):
    body = {"posted_date": "2026-11-03", "amount_cents": -1_250, "description": "Coffee", **fields}
    response = client.post("/api/transactions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


# --- Categories ---------------------------------------------------------------

def test_categories_include_the_ten_defaults(client):
    categories = client.get("/api/categories").json()

    assert len([c for c in categories if c["is_default"]]) == 10


def test_creating_a_category_and_the_duplicate_conflict(client):
    created = client.post("/api/categories", json={"name": "Pets"})
    duplicate = client.post("/api/categories", json={"name": "pets"})

    assert created.status_code == 201
    assert created.json()["is_default"] is False
    assert duplicate.status_code == 409


# --- Transactions: the normal flow ---------------------------------------------

def test_create_list_update_delete_a_transaction(client):
    groceries = category_id(client, "Groceries")

    created = add(client, amount_cents=-4_599, description="Metro", category_id=groceries)
    assert created["category_name"] == "Groceries"
    assert created["category_source"] == "user"

    listed = client.get("/api/transactions", params={"month": "2026-11"}).json()
    assert [t["id"] for t in listed] == [created["id"]]

    updated = client.put(f"/api/transactions/{created['id']}",
                         json={"posted_date": "2026-11-04", "amount_cents": -5_000, "description": "Metro"})
    assert updated.status_code == 200
    assert (updated.json()["amount_cents"], updated.json()["category_id"]) == (-5_000, None)

    assert client.delete(f"/api/transactions/{created['id']}").status_code == 204
    assert client.delete(f"/api/transactions/{created['id']}").status_code == 404  # already gone


def test_listing_only_returns_the_requested_month(client):
    add(client, posted_date="2026-10-31", description="October")
    add(client, posted_date="2026-11-01", description="November first")
    add(client, posted_date="2026-11-30", description="November last")
    add(client, posted_date="2026-12-01", description="December")

    november = client.get("/api/transactions", params={"month": "2026-11"}).json()

    assert [t["description"] for t in november] == ["November last", "November first"]  # newest first


@pytest.mark.parametrize("body_change, expected_status", [
    ({"amount_cents": 0}, 422),           # service rule
    ({"amount_cents": 12.5}, 422),        # not a whole number of cents (Pydantic)
    ({"posted_date": "2026-02-30"}, 422), # not a real date (Pydantic)
    ({"description": ""}, 422),           # service rule
    ({"category_id": 999_999}, 422),      # no such category
])
def test_bad_input_is_refused_with_422(client, body_change, expected_status):
    body = {"posted_date": "2026-11-03", "amount_cents": -100, "description": "x", **body_change}

    response = client.post("/api/transactions", json=body)

    assert response.status_code == expected_status
    assert "detail" in response.json()


def test_a_bad_month_is_refused(client):
    assert client.get("/api/transactions", params={"month": "2026-13"}).status_code == 422


# --- Isolation: user A must never see or change user B's data ------------------

def test_bob_cannot_see_alices_transactions(client, users):
    add(client, description="Alice's secret purchase")

    users.current = users.bob
    bobs_view = client.get("/api/transactions", params={"month": "2026-11"}).json()

    assert bobs_view == []


def test_bob_cannot_change_or_delete_alices_transaction(client, users):
    alices = add(client)

    users.current = users.bob
    update = client.put(f"/api/transactions/{alices['id']}",
                        json={"posted_date": "2026-11-03", "amount_cents": -1, "description": "hacked"})
    delete = client.delete(f"/api/transactions/{alices['id']}")

    assert (update.status_code, delete.status_code) == (404, 404)  # 404, not 403: don't even confirm it exists
    users.current = users.alice
    assert client.get("/api/transactions", params={"month": "2026-11"}).json()[0]["description"] == "Coffee"


def test_bob_cannot_see_or_use_alices_own_category(client, users):
    pets = client.post("/api/categories", json={"name": "Pets"}).json()

    users.current = users.bob
    assert "Pets" not in [c["name"] for c in client.get("/api/categories").json()]
    response = client.post("/api/transactions", json={
        "posted_date": "2026-11-03", "amount_cents": -100, "description": "x", "category_id": pets["id"]})
    assert response.status_code == 422


def test_bob_cannot_see_or_delete_alices_budget(client, users):
    budget = client.put("/api/budgets", json={
        "category_id": category_id(client, "Groceries"), "month": "2026-11", "limit_cents": 50_000}).json()

    users.current = users.bob
    assert client.get("/api/budgets", params={"month": "2026-11"}).json() == []
    assert client.delete(f"/api/budgets/{budget['id']}").status_code == 404


def test_bobs_dashboard_ignores_alices_spending(client, users):
    add(client, amount_cents=-99_999)

    users.current = users.bob
    dashboard = client.get("/api/dashboard", params={"month": "2026-11"}).json()

    assert (dashboard["spent_cents"], dashboard["categories"]) == (0, [])


# --- Budgets and the dashboard, end to end -------------------------------------

def test_setting_a_budget_twice_replaces_the_limit(client):
    groceries = category_id(client, "Groceries")

    first = client.put("/api/budgets", json={"category_id": groceries, "month": "2026-11", "limit_cents": 50_000})
    second = client.put("/api/budgets", json={"category_id": groceries, "month": "2026-11", "limit_cents": 60_000})

    assert first.json()["id"] == second.json()["id"]  # same row, updated
    assert second.json()["month"] == str(date(2026, 11, 1))
    assert [b["limit_cents"] for b in client.get("/api/budgets", params={"month": "2026-11"}).json()] == [60_000]


def test_dashboard_numbers_match_a_hand_calculation(client):
    # Arrange: in November, $2,800 salary, $45.99 + $120.00 groceries,
    # a $15.00 grocery refund, and $30.00 uncategorized. Budget: $150 groceries.
    groceries, income = category_id(client, "Groceries"), category_id(client, "Income")
    add(client, amount_cents=280_000, description="Salary", category_id=income)
    add(client, amount_cents=-4_599, description="Metro", category_id=groceries)
    add(client, amount_cents=-12_000, description="Costco", category_id=groceries)
    add(client, amount_cents=1_500, description="Refund", category_id=groceries)
    add(client, amount_cents=-3_000, description="Cash")
    add(client, posted_date="2026-10-15", amount_cents=-77_700, description="Last month, ignored")
    client.put("/api/budgets", json={"category_id": groceries, "month": "2026-11", "limit_cents": 15_000})

    # Act
    dashboard = client.get("/api/dashboard", params={"month": "2026-11"}).json()

    # Assert: groceries = 45.99 + 120.00 - 15.00 = $150.99 -> 1 cent over $150.
    by_name = {row["category_name"]: row for row in dashboard["categories"]}
    assert by_name["Groceries"]["spent_cents"] == 15_099
    assert by_name["Groceries"]["remaining_cents"] == -99
    assert by_name["Groceries"]["status"] == "over"
    assert by_name["Uncategorized"]["spent_cents"] == 3_000
    assert dashboard["income_cents"] == 280_000
    assert dashboard["spent_cents"] == 15_099 + 3_000   # $180.99
    assert dashboard["net_cents"] == 280_000 - 18_099   # $2,619.01
