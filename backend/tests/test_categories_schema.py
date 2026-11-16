"""Integration tests for the categories table (migration 002).

These check the rules the DATABASE enforces by itself, so they hold even if
the app code has a bug. Each test runs on a freshly migrated budget_test,
as the owner, so row-level security (test_row_level_security.py) stays out
of the way: these tests are about the table's own rules.
"""

import psycopg
import pytest


# 002 creates the first nine; 003 adds Income.
DEFAULTS = ["Groceries", "Rent", "Utilities", "Transport", "Dining out",
            "Entertainment", "Health", "Shopping", "Other", "Income"]


@pytest.fixture
def make_user(owner):
    def make(email):
        with owner() as conn:
            return conn.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (email,)).fetchone()["id"]
    return make


@pytest.fixture
def add_category(owner):
    def add(name, user_id=None):
        with owner() as conn:
            conn.execute("INSERT INTO categories (user_id, name) VALUES (%s, %s)", (user_id, name))
    return add


def test_default_categories_are_created(migrated, owner):
    with owner() as conn:
        rows = conn.execute("SELECT name FROM categories WHERE user_id IS NULL ORDER BY id").fetchall()

    assert [r["name"] for r in rows] == DEFAULTS


def test_two_defaults_cannot_share_a_name_ignoring_case(migrated, add_category):
    with pytest.raises(psycopg.errors.UniqueViolation):
        add_category("groceries")  # "Groceries" already exists


def test_a_user_cannot_have_two_categories_with_the_same_name(migrated, make_user, add_category):
    alice = make_user("alice@example.com")
    add_category("Pets", alice)

    with pytest.raises(psycopg.errors.UniqueViolation):
        add_category("PETS", alice)


def test_two_users_can_each_have_a_category_with_the_same_name(migrated, make_user, add_category):
    alice, bob = make_user("alice@example.com"), make_user("bob@example.com")

    add_category("Pets", alice)
    add_category("Pets", bob)  # no error: different users


@pytest.mark.parametrize("bad_name", ["", "   ", "x" * 51])
def test_empty_or_too_long_names_are_rejected(migrated, add_category, bad_name):
    with pytest.raises(psycopg.errors.CheckViolation):
        add_category(bad_name)


def test_deleting_a_user_deletes_their_categories_but_not_the_defaults(migrated, owner, make_user, add_category):
    alice = make_user("alice@example.com")
    add_category("Pets", alice)

    with owner() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (alice,))
        remaining = conn.execute("SELECT count(*) AS n FROM categories WHERE user_id IS NOT NULL").fetchone()["n"]
        defaults = conn.execute("SELECT count(*) AS n FROM categories WHERE user_id IS NULL").fetchone()["n"]

    assert remaining == 0
    assert defaults == len(DEFAULTS)
