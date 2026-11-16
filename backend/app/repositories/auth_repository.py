from datetime import datetime

from app.db import get_connection


class AuthRepository:
    # --- Users ----------------------------------------------------------------

    def find_user_by_email(self, email: str) -> dict | None:
        with get_connection() as conn:
            return conn.execute(
                "SELECT id, email, password_hash FROM users WHERE lower(email) = lower(%s)", (email,)
            ).fetchone()

    def get_user(self, user_id: int) -> dict | None:
        with get_connection() as conn:
            return conn.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE id = %s", (user_id,)
            ).fetchone()

    def create_user(self, email: str, password_hash: str) -> dict | None:
        """None if the email is already taken (checked by the database, so two
        sign-ups at the same moment can't both succeed)."""
        with get_connection() as conn:
            return conn.execute(
                """
                INSERT INTO users (email, password_hash) VALUES (%s, %s)
                ON CONFLICT (lower(email)) DO NOTHING
                RETURNING id, email
                """,
                (email, password_hash),
            ).fetchone()

    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        with get_connection() as conn:
            conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))

    def delete_user(self, user_id: int) -> None:
        """Deletes the user and, through ON DELETE CASCADE, all their data."""
        with get_connection() as conn:
            conn.execute("DELETE FROM users WHERE id = %s", (user_id,))

    # --- Sessions -------------------------------------------------------------

    def create_session(self, token_hash: str, user_id: int, expires_at: datetime) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
                (token_hash, user_id, expires_at),
            )

    def user_id_for_session(self, token_hash: str) -> int | None:
        """The session's user, or None if it doesn't exist or has expired."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT user_id FROM sessions WHERE token_hash = %s AND expires_at > now()", (token_hash,)
            ).fetchone()
            return row["user_id"] if row else None

    def delete_session(self, token_hash: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))

    def delete_expired_sessions(self) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at <= now()")

    # --- Rate limiting --------------------------------------------------------

    def record_failure(self, email: str) -> None:
        with get_connection() as conn:
            conn.execute("INSERT INTO login_failures (email) VALUES (%s)", (email,))

    def recent_failures(self, email: str, since: datetime) -> int:
        with get_connection() as conn:
            return conn.execute(
                "SELECT count(*) AS n FROM login_failures WHERE lower(email) = lower(%s) AND attempted_at > %s",
                (email, since),
            ).fetchone()["n"]

    def clear_failures(self, email: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM login_failures WHERE lower(email) = lower(%s)", (email,))

    # --- Data export ----------------------------------------------------------

    def export_user_data(self, user_id: int) -> dict:
        """Everything stored about the user, for "download my data"."""
        with get_connection(user_id) as conn:
            def rows(sql):
                return conn.execute(sql, (user_id,)).fetchall()

            return {
                "account": conn.execute(
                    "SELECT id, email, created_at FROM users WHERE id = %s", (user_id,)
                ).fetchone(),
                "categories": rows("SELECT id, name, created_at FROM categories WHERE user_id = %s ORDER BY id"),
                "transactions": rows(
                    """SELECT t.id, t.posted_date, t.amount_cents, t.description, c.name AS category,
                              t.category_source, t.created_at
                       FROM transactions t LEFT JOIN categories c ON c.id = t.category_id
                       WHERE t.user_id = %s ORDER BY t.posted_date, t.id"""
                ),
                "budgets": rows(
                    """SELECT b.month, c.name AS category, b.limit_cents
                       FROM budgets b JOIN categories c ON c.id = b.category_id
                       WHERE b.user_id = %s ORDER BY b.month, c.name"""
                ),
            }
