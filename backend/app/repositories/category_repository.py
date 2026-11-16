from app.db import get_connection

# A user sees the default categories (user_id NULL) plus their own.
_VISIBLE = "(user_id IS NULL OR user_id = %(user_id)s)"
_COLUMNS = "id, name, user_id IS NULL AS is_default"


class CategoryRepository:
    def list_visible(self, user_id: int) -> list[dict]:
        with get_connection(user_id) as conn:
            return conn.execute(
                f"SELECT {_COLUMNS} FROM categories WHERE {_VISIBLE} ORDER BY lower(name)",
                {"user_id": user_id},
            ).fetchall()

    def get_visible(self, user_id: int, category_id: int) -> dict | None:
        with get_connection(user_id) as conn:
            return conn.execute(
                f"SELECT {_COLUMNS} FROM categories WHERE id = %(id)s AND {_VISIBLE}",
                {"id": category_id, "user_id": user_id},
            ).fetchone()

    def name_taken(self, user_id: int, name: str, except_id: int | None = None) -> bool:
        """True if a default or one of the user's own categories (other than
        except_id) already has this name."""
        with get_connection(user_id) as conn:
            return conn.execute(
                f"""SELECT 1 FROM categories
                    WHERE lower(name) = lower(%(name)s) AND {_VISIBLE} AND id IS DISTINCT FROM %(except_id)s""",
                {"name": name, "user_id": user_id, "except_id": except_id},
            ).fetchone() is not None

    def rename_own(self, user_id: int, category_id: int, name: str) -> dict | None:
        """None unless the category is this user's own (defaults can't be renamed)."""
        with get_connection(user_id) as conn:
            return conn.execute(
                f"UPDATE categories SET name = %s WHERE id = %s AND user_id = %s RETURNING {_COLUMNS}",
                (name, category_id, user_id),
            ).fetchone()

    def delete_own(self, user_id: int, category_id: int) -> bool:
        """Its transactions become uncategorized and its budgets go (see migrations 003, 004)."""
        with get_connection(user_id) as conn:  # one transaction: both steps or neither
            # ON DELETE SET NULL clears category_id; also say nobody chose a category now.
            conn.execute(
                "UPDATE transactions SET category_source = 'none' WHERE category_id = %s AND user_id = %s",
                (category_id, user_id),
            )
            deleted = conn.execute(
                "DELETE FROM categories WHERE id = %s AND user_id = %s", (category_id, user_id)
            )
            return deleted.rowcount == 1

    def create(self, user_id: int, name: str) -> dict:
        with get_connection(user_id) as conn:
            return conn.execute(
                f"INSERT INTO categories (user_id, name) VALUES (%s, %s) RETURNING {_COLUMNS}",
                (user_id, name),
            ).fetchone()
