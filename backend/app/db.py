"""The Postgres connection pool.

The pool is opened once when the app starts and closed when it stops.
Repositories borrow a connection for each piece of work:

    with get_connection() as conn:
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
    except Exception:
        pool.close()
        raise
    _pool = pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Borrow a connection from the pool and give it back afterwards.

    If the block finishes normally the work is committed; if it raises an
    error, everything it did is rolled back (undone).
    """
    if _pool is None:
        raise RuntimeError("database pool is not open; call open_pool() first")
    with _pool.connection() as conn:
        yield conn
