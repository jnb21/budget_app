"""App settings, read once from environment variables and the .env file.

Every other file gets its settings from get_settings(); nothing else reads
os.environ or .env directly, so there is one place to look.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# budget_app/.env (this file is budget_app/backend/app/config.py)
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Real environment variables win over .env, so a server or a test can
    # override any value. Keys in .env we don't use (POSTGRES_*) are ignored.
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # Two logins (README, "Two database logins"):
    database_url: str                 # the app's login: reads and writes rows only (required)
    migration_database_url: str | None = None  # the owner: creates tables and rules (migrations only)
    db_pool_min_size: int = 1         # connections kept open even when idle
    db_pool_max_size: int = 5         # most connections open at the same time
    db_connect_timeout: float = 10.0  # seconds to wait for Postgres at startup
    session_days: int = 30            # how long a login lasts
    cookie_secure: bool = False       # True in production: the cookie is only sent over HTTPS

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def must_be_postgres(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("postgresql://", "postgres://")):
            raise ValueError("database URLs must start with postgresql://")
        return value


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them (lru_cache remembers the result)."""
    return Settings()
