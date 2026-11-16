"""Integration tests for row-level security (migration 006), on budget_test.

Every query here is raw SQL run as the app's own login, and most of them
have NO "WHERE user_id = ...": they show that Postgres itself hides and
protects other users' rows, so a repository that forgets its filter still
can't leak or damage anyone else's data.

Setup and final checks run as the owner, who sees every row.
"""

import psycopg
import pytest

from app import db


@pytest.fixture
def alice_and_bob(migrated, owner):
    """Two users, each with a category, a transaction and a budget."""
    ids = {}
    with owner() as conn:
        for name in ("alice", "bob"):
            user = conn.execute("INSERT INTO users (email) VALUES (%s) RETURNING id",
                                (f"{name}@example.com",)).fetchone()["id"]
            category = conn.execute("INSERT INTO categories (user_id, name) VALUES (%s, %s) RETURNING id",
                                    (user, f"{name}'s category")).fetchone()["id"]
            conn.execute("""INSERT INTO transactions (user_id, posted_date, amount_cents, description, category_id)
                            VALUES (%s, '2026-11-03', -1000, %s, %s)""", (user, f"{name}'s coffee", category))
            conn.execute("INSERT INTO budgets (user_id, category_id, month, limit_cents) VALUES (%s, %s, '2026-11-01', 5000)",
                         (user, category))
            ids[name] = user
    return ids


def as_user(user_id, sql, params=()):
    """Run one statement as the app's login, for user_id (None = no user set)."""
    with db.get_connection(user_id) as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchall() if cursor.description else cursor.rowcount


# --- Reading --------------------------------------------------------------------

@pytest.mark.parametrize("table", ["transactions", "budgets"])
def test_a_user_sees_only_their_own_rows(alice_and_bob, table):
    rows = as_user(alice_and_bob["alice"], f"SELECT user_id FROM {table}")  # no WHERE at all

    assert {r["user_id"] for r in rows} == {alice_and_bob["alice"]}


def test_a_user_sees_the_defaults_and_their_own_categories_only(alice_and_bob):
    rows = as_user(alice_and_bob["alice"], "SELECT user_id FROM categories")

    assert {r["user_id"] for r in rows} == {None, alice_and_bob["alice"]}


def test_with_no_user_set_no_ones_rows_are_visible(alice_and_bob):
    assert as_user(None, "SELECT * FROM transactions") == []
    assert as_user(None, "SELECT * FROM budgets") == []
    assert {r["user_id"] for r in as_user(None, "SELECT user_id FROM categories")} == {None}  # defaults only


def test_the_user_does_not_carry_over_to_the_next_request(alice_and_bob):
    as_user(alice_and_bob["alice"], "SELECT 1")

    assert as_user(None, "SELECT * FROM transactions") == []  # same pool, maybe the same connection


# --- Writing --------------------------------------------------------------------

@pytest.mark.parametrize("sql", [
    "INSERT INTO transactions (user_id, posted_date, amount_cents, description) VALUES (%(bob)s, '2026-11-04', -1, 'x')",
    "INSERT INTO categories (user_id, name) VALUES (%(bob)s, 'planted')",
    "INSERT INTO budgets (user_id, category_id, month, limit_cents) VALUES (%(bob)s, 1, '2026-12-01', 100)",
])
def test_a_user_cannot_create_rows_for_someone_else(alice_and_bob, sql):
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
        as_user(alice_and_bob["alice"], sql, alice_and_bob)


@pytest.mark.parametrize("table", ["transactions", "budgets", "categories"])
def test_a_user_cannot_hand_their_rows_to_someone_else(alice_and_bob, table):
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
        as_user(alice_and_bob["alice"], f"UPDATE {table} SET user_id = %(bob)s", alice_and_bob)


@pytest.mark.parametrize("sql", [
    "UPDATE transactions SET amount_cents = 1",
    "DELETE FROM transactions",
    "UPDATE budgets SET limit_cents = 1",
    "DELETE FROM budgets",
    "UPDATE categories SET name = 'hacked' WHERE user_id IS NOT NULL",
    "DELETE FROM categories WHERE user_id IS NOT NULL",
])
def test_a_user_cannot_change_or_delete_someone_elses_rows(alice_and_bob, owner, sql):
    changed = as_user(alice_and_bob["bob"], sql)
    assert changed == 1  # only Bob's own row...

    with owner() as conn:  # ...and Alice's are untouched
        alices = conn.execute("""
            SELECT (SELECT count(*) FROM transactions WHERE user_id = %(alice)s AND amount_cents = -1000)
                 + (SELECT count(*) FROM budgets WHERE user_id = %(alice)s AND limit_cents = 5000)
                 + (SELECT count(*) FROM categories WHERE user_id = %(alice)s AND name = 'alice''s category') AS n
        """, alice_and_bob).fetchone()["n"]
    assert alices == 3


def test_default_categories_are_readable_but_cannot_be_changed(alice_and_bob):
    alice = alice_and_bob["alice"]

    assert as_user(alice, "UPDATE categories SET name = 'Food' WHERE name = 'Groceries'") == 0
    assert as_user(alice, "DELETE FROM categories WHERE user_id IS NULL") == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
        as_user(alice, "INSERT INTO categories (user_id, name) VALUES (NULL, 'New default')")


def test_deleting_a_user_still_removes_all_their_data(alice_and_bob, owner):
    # ON DELETE CASCADE is done by Postgres itself, not limited by the rules.
    as_user(None, "DELETE FROM users WHERE id = %(alice)s", alice_and_bob)

    with owner() as conn:
        left = conn.execute("""
            SELECT (SELECT count(*) FROM transactions WHERE user_id = %(alice)s)
                 + (SELECT count(*) FROM budgets WHERE user_id = %(alice)s)
                 + (SELECT count(*) FROM categories WHERE user_id = %(alice)s) AS n
        """, alice_and_bob).fetchone()["n"]
    assert left == 0


# --- What the app's login can't do at all ---------------------------------------------

@pytest.mark.parametrize("sql", [
    "ALTER TABLE transactions DISABLE ROW LEVEL SECURITY",  # switch the rules off
    "DROP POLICY own_rows ON transactions",
    "CREATE TABLE sneaky (id int)",
    "DELETE FROM schema_migrations",
])
def test_the_app_login_cannot_change_the_rules_or_the_schema(migrated, sql):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        as_user(None, sql)


# --- A guard for future migrations ------------------------------------------------------

def test_every_table_is_usable_by_the_app_and_user_tables_have_rls(migrated, owner):
    """Fails when a new migration adds a table but forgets its GRANT, or adds
    a table with a user_id column but forgets to turn on row-level security."""
    with owner() as conn:
        tables = conn.execute("""
            SELECT c.relname AS name, c.relrowsecurity AS rls,
                   has_table_privilege('budget_rw', c.oid, 'SELECT, INSERT, UPDATE, DELETE') AS granted,
                   EXISTS (SELECT 1 FROM pg_attribute a
                           WHERE a.attrelid = c.oid AND a.attname = 'user_id' AND NOT a.attisdropped) AS per_user
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'schema_migrations'
        """).fetchall()

    assert {t["name"] for t in tables if not t["granted"]} == set()
    # sessions is the one exception: login looks it up before the user is known (see 006).
    assert {t["name"] for t in tables if t["per_user"] and not t["rls"]} == {"sessions"}
