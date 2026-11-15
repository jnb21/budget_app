"""Architecture tests: check how the code is organized, not what it does.

The rule: nothing in app/agent/ may reach the database directly. It must go
through services. This test reads the agent's source files (without running
them) and lists every import, so a forbidden one fails the build.
"""

import ast
import sys
from pathlib import Path

import pytest

import app

APP_DIR = Path(app.__file__).resolve().parent
AGENT_DIR = APP_DIR / "agent"
FORBIDDEN = ("app.repositories", "app.db", "psycopg", "psycopg_pool")


def imported_modules(path: Path) -> list[tuple[int, str]]:
    """(line number, full module name) for every import in a Python file.

    "from app import db" counts as importing "app.db", and relative imports
    ("from ..repositories import x") are resolved to their full name.
    """
    package = ".".join(path.relative_to(APP_DIR.parent).with_suffix("").parts[:-1])
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative: one dot = this package, two dots = its parent...
                base = ".".join(package.split(".")[: len(package.split(".")) - node.level + 1])
                module = f"{base}.{node.module}" if node.module else base
            else:
                module = node.module
            found.append((node.lineno, module))
            found += [(node.lineno, f"{module}.{alias.name}") for alias in node.names]
    return found


def forbidden_imports(path: Path) -> list[str]:
    return [
        f"{path.relative_to(APP_DIR.parent)}:{line} imports {module}"
        for line, module in imported_modules(path)
        if any(module == f or module.startswith(f + ".") for f in FORBIDDEN)
    ]


# --- The real rule, on the real agent folder --------------------------------

def test_agent_code_never_reaches_the_database_directly():
    violations = [v for path in sorted(AGENT_DIR.rglob("*.py")) for v in forbidden_imports(path)]

    assert violations == [], "agent/ must call services, not:\n" + "\n".join(violations)


# --- Prove the checker itself works (a checker that finds nothing is useless) ---

@pytest.fixture
def agent_file(tmp_path, monkeypatch):
    """Write a pretend app/agent/tools.py in a temporary copy of the layout."""
    monkeypatch.setattr(sys.modules[__name__], "APP_DIR", tmp_path / "app")  # point the checker at the temp copy
    path = tmp_path / "app" / "agent" / "tools.py"
    path.parent.mkdir(parents=True)

    def write(source: str) -> Path:
        path.write_text(source, encoding="utf-8")
        return path

    return write


@pytest.mark.parametrize("source", [
    "from app.repositories.health_repository import HealthRepository",
    "import app.repositories.health_repository",
    "from app import db",
    "from app.db import get_connection",
    "import psycopg",
    "from psycopg_pool import ConnectionPool",
    "from ..repositories import health_repository",   # relative import
    "from .. import db",                              # relative import
])
def test_checker_catches_forbidden_imports(agent_file, source):
    assert forbidden_imports(agent_file(source)) != []


@pytest.mark.parametrize("source", [
    "from app.services.health_service import HealthService",
    "from app.config import get_settings",
    "import json",
    "from .prompts import SYSTEM_PROMPT",              # another agent file
    "from app.dbutils import helper",                 # starts with 'app.db' but is a different module
])
def test_checker_allows_other_imports(agent_file, source):
    assert forbidden_imports(agent_file(source)) == []
