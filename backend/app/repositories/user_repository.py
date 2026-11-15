from app.db import get_connection


class UserRepository:
    def get_or_create(self, email: str) -> int:
        """The id of the user with this email, creating the user if needed."""
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (email) VALUES (%s) ON CONFLICT (lower(email)) DO NOTHING",
                (email,),
            )
            return conn.execute(
                "SELECT id FROM users WHERE lower(email) = lower(%s)", (email,)
            ).fetchone()["id"]
