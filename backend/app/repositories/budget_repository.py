from datetime import date

from app.db import get_connection

_SELECT = """
    SELECT b.id, b.category_id, c.name AS category_name, b.month, b.limit_cents
    FROM budgets b
    JOIN categories c ON c.id = b.category_id
"""


class BudgetRepository:
    def list_for_month(self, user_id: int, month: date) -> list[dict]:
        with get_connection() as conn:
            return conn.execute(
                _SELECT + " WHERE b.user_id = %s AND b.month = %s ORDER BY lower(c.name)",
                (user_id, month),
            ).fetchall()

    def upsert(self, user_id: int, category_id: int, month: date, limit_cents: int) -> dict:
        """Create the budget, or change its limit if one already exists for that category and month."""
        with get_connection() as conn:
            budget_id = conn.execute(
                """
                INSERT INTO budgets (user_id, category_id, month, limit_cents)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, category_id, month)
                DO UPDATE SET limit_cents = EXCLUDED.limit_cents, updated_at = now()
                RETURNING id
                """,
                (user_id, category_id, month, limit_cents),
            ).fetchone()["id"]
            return conn.execute(_SELECT + " WHERE b.id = %s", (budget_id,)).fetchone()

    def delete(self, user_id: int, budget_id: int) -> bool:
        with get_connection() as conn:
            deleted = conn.execute(
                "DELETE FROM budgets WHERE id = %s AND user_id = %s", (budget_id, user_id)
            )
            return deleted.rowcount == 1
