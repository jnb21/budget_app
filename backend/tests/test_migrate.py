"""Tests for migrate.py.

The first group are unit tests (no database): they only look at file names.
The rest are integration tests on budget_test, using small fake migration
files written to a temporary folder, so each test controls exactly which
migrations exist.
"""

import pytest

from app import db
from app.migrate import MIGRATIONS_DIR, apply_migrations, find_migrations


def write(folder, name, sql):
    (folder / name).write_text(sql, encoding="utf-8")


def table_exists(name):
    with db.get_connection() as conn:
        return conn.execute("SELECT to_regclass(%s) AS found", (name,)).fetchone()["found"] is not None


def recorded_migrations():
    with db.get_connection() as conn:
        return [r["filename"] for r in conn.execute("SELECT filename FROM schema_migrations ORDER BY filename")]


# --- Unit tests: file names only -------------------------------------------

def test_migrations_are_found_in_number_order(tmp_path):
    write(tmp_path, "002_second.sql", "")
    write(tmp_path, "010_tenth.sql", "")
    write(tmp_path, "001_first.sql", "")

    names = [p.name for p in find_migrations(tmp_path)]

    assert names == ["001_first.sql", "002_second.sql", "010_tenth.sql"]


@pytest.mark.parametrize("bad_name", ["1_users.sql", "001-users.sql", "001_Users.sql", "users.sql"])
def test_badly_named_file_is_rejected(tmp_path, bad_name):
    write(tmp_path, bad_name, "")

    with pytest.raises(ValueError, match="bad migration file name"):
        find_migrations(tmp_path)


def test_two_files_with_the_same_number_are_rejected(tmp_path):
    write(tmp_path, "003_add_a.sql", "")
    write(tmp_path, "003_add_b.sql", "")

    with pytest.raises(ValueError, match="share the number 003"):
        find_migrations(tmp_path)


# --- Integration tests: real Postgres (budget_test) ------------------------

def test_pending_migrations_are_applied_in_order_and_recorded(empty_database, tmp_path):
    write(tmp_path, "001_create_a.sql", "CREATE TABLE a (id int);")
    write(tmp_path, "002_create_b.sql", "CREATE TABLE b (a_id int);")

    applied = apply_migrations(tmp_path)

    assert applied == ["001_create_a.sql", "002_create_b.sql"]
    assert table_exists("a") and table_exists("b")
    assert recorded_migrations() == ["001_create_a.sql", "002_create_b.sql"]


def test_running_again_applies_nothing(empty_database, tmp_path):
    write(tmp_path, "001_create_a.sql", "CREATE TABLE a (id int);")
    apply_migrations(tmp_path)

    applied_second_time = apply_migrations(tmp_path)  # would fail if 001 ran again: "a" exists

    assert applied_second_time == []


def test_only_the_new_file_is_applied_later(empty_database, tmp_path):
    write(tmp_path, "001_create_a.sql", "CREATE TABLE a (id int);")
    apply_migrations(tmp_path)
    write(tmp_path, "002_add_column.sql", "ALTER TABLE a ADD COLUMN note text;")

    applied = apply_migrations(tmp_path)

    assert applied == ["002_add_column.sql"]


def test_a_failing_migration_undoes_the_whole_run(empty_database, tmp_path):
    write(tmp_path, "001_create_a.sql", "CREATE TABLE a (id int);")
    write(tmp_path, "002_broken.sql", "CREATE TABLE oops (id not_a_real_type);")

    with pytest.raises(Exception, match="not_a_real_type"):
        apply_migrations(tmp_path)

    assert not table_exists("a")              # 001 was undone too
    assert not table_exists("schema_migrations")  # nothing recorded at all


def test_the_real_migrations_apply_to_an_empty_database(empty_database):
    applied = apply_migrations(MIGRATIONS_DIR)

    assert applied[0] == "001_create_users.sql"
    assert table_exists("users")
