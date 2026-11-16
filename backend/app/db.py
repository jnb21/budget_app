"""The Postgres connection pool.

The pool is opened once when the app starts and closed when it stops.
Repositories borrow a connection for each piece of work, saying which user
it is for, so row-level security (migration 006) shows only that user's rows:

    with get_connection(user_id) as conn:
        conn.execute("SELECT ...")

Only repositories should import this module.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import Settings

_pool: ConnectionPool | None = None


def open_pool(settings: Settings) -> None:
    """Open the pool and wait until at least one connection works.

    Waits up to settings.db_connect_timeout seconds, then fails fast
    (psycopg_pool.PoolTimeout) if Postgres is down or the password is wrong,
    instead of failing later on the first request.
    """
    global _pool
    if _pool is not None:
        return
    pool = ConnectionPool(
        settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        kwargs={"row_factory": dict_row},  # rows come back as dicts: {"id": 1, ...}
        # Before lending a connection, check it still works (a tiny round trip).
        # A connection that died while idle is replaced instead of failing a request.
        check=ConnectionPool.check_connection,
        open=False,
    )
    try:
        pool.open(wait=True, timeout=settings.db_connect_timeout)
        with pool.connection() as conn:
            _refuse_logins_that_skip_row_security(conn)
    except Exception:
        pool.close()
        raise
    _pool = pool


def _refuse_logins_that_skip_row_security(conn: psycopg.Connection) -> None:
    """Superusers, BYPASSRLS roles and table owners skip row-level security
    without any error, so the app would quietly lose that protection. Better
    to refuse to start."""
    row = conn.execute("""
        SELECT rolsuper OR rolbypassrls
               OR EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tableowner = current_user)
               AS skips
        FROM pg_roles WHERE rolname = current_user
    """).fetchone()
    if row["skips"]:
        raise RuntimeError(
            "DATABASE_URL's login skips row-level security (superuser, BYPASSRLS or table owner); "
            "use the app's own login, see README 'Two database logins'"
        )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection(user_id: int | None = None) -> Iterator[psycopg.Connection]:
    """Borrow a connection from the pool and give it back afterwards.

    user_id: the user this work is for (see act_as). Leave it out only for
    work that touches no user's rows (the health check, logging in).

    If the block finishes normally the work is committed; if it raises an
    error, everything it did is rolled back (undone).
    """
    if _pool is None:
        raise RuntimeError("database pool is not open; call open_pool() first")
    with _pool.connection() as conn:
        if user_id is not None:
            act_as(conn, user_id)
        yield conn


def act_as(conn: psycopg.Connection, user_id: int) -> None:
    """Tell Postgres which user's rows this transaction may see and change.
    true = for this transaction only: it can't leak to the next request."""
    conn.execute("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
