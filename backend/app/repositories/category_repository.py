from app.db import get_connection

# A user sees the default categories (user_id NULL) plus their own.
_VISIBLE = "(user_id IS NULL OR user_id = %(user_id)s)"
_COLUMNS = "id, name, user_id IS NULL AS is_default"


class CategoryRepository:
    def list_visible(self, user_id: int) -> list[dict]:
        with get_connection() as conn:
            return conn.execute(
                f"SELECT {_COLUMNS} FROM categories WHERE {_VISIBLE} ORDER BY lower(name)",
                {"user_id": user_id},
            ).fetchall()

    def get_visible(self, user_id: int, category_id: int) -> dict | None:
        with get_connection() as conn:
            return conn.execute(
                f"SELECT {_COLUMNS} FROM categories WHERE id = %(id)s AND {_VISIBLE}",
                {"id": category_id, "user_id": user_id},
            ).fetchone()

    def name_taken(self, user_id: int, name: str) -> bool:
        """True if a default or one of the user's own categories already has this name."""
        with get_connection() as conn:
            return conn.execute(
                f"SELECT 1 FROM categories WHERE lower(name) = lower(%(name)s) AND {_VISIBLE}",
                {"name": name, "user_id": user_id},
            ).fetchone() is not None

    def create(self, user_id: int, name: str) -> dict:
        with get_connection() as conn:
            return conn.execute(
                f"INSERT INTO categories (user_id, name) VALUES (%s, %s) RETURNING {_COLUMNS}",
                (user_id, name),
            ).fetchone()
