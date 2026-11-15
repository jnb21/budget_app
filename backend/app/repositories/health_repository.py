"""SQL for the health check.

A repository only talks to the database: it runs SQL and returns plain
Python values. It makes no decisions; deciding what a result means is the
service's job.
"""

from app.db import get_connection


class HealthRepository:
    def ping(self) -> None:
        """Run the smallest possible query.

        Returns nothing when the database answers. If it can't (pool not
        open, Postgres down), the error is raised to the caller unchanged.
        """
        with get_connection() as conn:
            conn.execute("SELECT 1")
