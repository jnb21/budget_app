"""Unit tests for config.py: no database, no real .env file.

Settings(_env_file=...) lets each test choose which .env file is read
(None = none at all), and monkeypatch sets or removes environment variables
for one test only, then puts them back.
"""

import pytest
from pydantic import ValidationError

from app.config import Settings

URL = "postgresql://user:secret@localhost:5433/budget"


def test_reads_database_url_from_environment(monkeypatch):
    # Arrange
    monkeypatch.setenv("DATABASE_URL", URL)
    # Act
    settings = Settings(_env_file=None)
    # Assert
    assert settings.database_url == URL


def test_reads_database_url_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"DATABASE_URL={URL}\nPOSTGRES_USER=ignored\n")

    settings = Settings(_env_file=env_file)

    assert settings.database_url == URL


def test_environment_variable_wins_over_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://from-file/budget\n")
    monkeypatch.setenv("DATABASE_URL", "postgresql://from-environment/budget")

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "postgresql://from-environment/budget"


def test_pool_settings_have_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)

    settings = Settings(_env_file=None)

    assert (settings.db_pool_min_size, settings.db_pool_max_size) == (1, 5)
    assert settings.db_connect_timeout == 10.0


def test_missing_database_url_is_an_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_non_postgres_url_is_rejected(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://user:secret@localhost/budget")

    with pytest.raises(ValidationError, match="must start with postgresql://"):
        Settings(_env_file=None)
