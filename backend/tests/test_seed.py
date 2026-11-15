"""Integration tests for the fake-data seed script (budget_test)."""

from datetime import date

import pytest

from app import db
from app.dependencies import DEMO_USER_EMAIL
from app.migrate import apply_migrations
from app.seed import BUDGETS, MONTHS, fake_transactions, seed_demo_data

TODAY = date(2026, 11, 15)


@pytest.fixture
def migrated(empty_database):
    apply_migrations()


def count(sql, *params):
    with db.get_connection() as conn:
        return conn.execute(sql, params).fetchone()["n"]


def test_seeding_twice_gives_the_same_data(migrated):
    first = seed_demo_data(TODAY)
    second = seed_demo_data(TODAY)

    assert first == second
    assert count("SELECT count(*) AS n FROM transactions") == first["transactions"]
    assert count("SELECT count(*) AS n FROM budgets") == MONTHS * len(BUDGETS)


def test_seeding_never_touches_other_users(migrated):
    with db.get_connection() as conn:
        alice = conn.execute("INSERT INTO users (email) VALUES ('alice@example.com') RETURNING id").fetchone()["id"]
        conn.execute("INSERT INTO transactions (user_id, posted_date, amount_cents, description) "
                     "VALUES (%s, '2026-11-01', -100, 'mine')", (alice,))

    seed_demo_data(TODAY)

    assert count("SELECT count(*) AS n FROM transactions WHERE user_id = %s", alice) == 1


def test_fake_data_is_believable():
    rows = fake_transactions(TODAY)

    assert all(day <= TODAY for day, *_ in rows)                   # nothing in the future
    assert all(cents != 0 for _, _, cents, _ in rows)              # the table refuses 0
    assert {day.replace(day=1) for day, *_ in rows} == {date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)}


def test_fake_data_is_the_same_every_time():
    assert fake_transactions(TODAY) == fake_transactions(TODAY)


def test_month_list_crosses_the_new_year():
    assert {day.replace(day=1) for day, *_ in fake_transactions(date(2027, 1, 10))} == {
        date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1)}


def test_the_demo_user_is_the_one_the_app_uses(migrated):
    seed_demo_data(TODAY)

    assert count("SELECT count(*) AS n FROM users WHERE email = %s", DEMO_USER_EMAIL) == 1
