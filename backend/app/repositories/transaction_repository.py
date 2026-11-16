from dataclasses import asdict, dataclass
from datetime import date

from app.db import get_connection


@dataclass(frozen=True)
class TransactionData:
    """The fields a service hands over to save (already validated)."""

    posted_date: date
    amount_cents: int
    description: str
    category_id: int | None
    category_source: str


_SELECT = """
    SELECT t.id, t.posted_date, t.amount_cents, t.description,
           t.category_id, c.name AS category_name, t.category_source
    FROM transactions t
    LEFT JOIN categories c ON c.id = t.category_id
"""


class TransactionRepository:
    def list_between(self, user_id: int, start: date, end: date) -> list[dict]:
        """The user's transactions with start <= posted_date < end, newest first."""
        with get_connection(user_id) as conn:
            return conn.execute(
                _SELECT + """
                WHERE t.user_id = %s AND t.posted_date >= %s AND t.posted_date < %s
                ORDER BY t.posted_date DESC, t.id DESC
                """,
                (user_id, start, end),
            ).fetchall()

    def get(self, user_id: int, transaction_id: int) -> dict | None:
        with get_connection(user_id) as conn:
            return conn.execute(
                _SELECT + " WHERE t.user_id = %s AND t.id = %s", (user_id, transaction_id)
            ).fetchone()

    def create(self, user_id: int, data: TransactionData) -> dict:
        with get_connection(user_id) as conn:
            new_id = conn.execute(
                """
                INSERT INTO transactions
                    (user_id, posted_date, amount_cents, description, category_id, category_source)
                VALUES (%(user_id)s, %(posted_date)s, %(amount_cents)s, %(description)s,
                        %(category_id)s, %(category_source)s)
                RETURNING id
                """,
                {"user_id": user_id, **asdict(data)},
            ).fetchone()["id"]
            return conn.execute(_SELECT + " WHERE t.id = %s", (new_id,)).fetchone()

    def update(self, user_id: int, transaction_id: int, data: TransactionData) -> dict | None:
        """None if the transaction doesn't exist or isn't this user's."""
        with get_connection(user_id) as conn:
            row = conn.execute(
                """
                UPDATE transactions
                SET posted_date = %(posted_date)s, amount_cents = %(amount_cents)s,
                    description = %(description)s, category_id = %(category_id)s,
                    category_source = %(category_source)s
                WHERE id = %(id)s AND user_id = %(user_id)s
                RETURNING id
                """,
                {"id": transaction_id, "user_id": user_id, **asdict(data)},
            ).fetchone()
            if row is None:
                return None
            return conn.execute(_SELECT + " WHERE t.id = %s", (transaction_id,)).fetchone()

    def delete(self, user_id: int, transaction_id: int) -> bool:
        with get_connection(user_id) as conn:
            deleted = conn.execute(
                "DELETE FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, user_id)
            )
            return deleted.rowcount == 1

    def net_by_category(self, user_id: int, start: date, end: date) -> list[dict]:
        """Sum of amounts per category in the date range (category_id None = uncategorized)."""
        with get_connection(user_id) as conn:
            return conn.execute(
                """
                SELECT t.category_id, c.name AS category_name, sum(t.amount_cents)::bigint AS net_cents
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = %s AND t.posted_date >= %s AND t.posted_date < %s
                GROUP BY t.category_id, c.name
                """,
                (user_id, start, end),
            ).fetchall()
