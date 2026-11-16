"""Builds the FastAPI app and wires the layers together.

Run the server (from backend/):  .venv/bin/uvicorn app.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg_pool import PoolTimeout

from app import db
from app.config import Settings, get_settings
from app.errors import (
    ConflictError, InvalidInputError, NotFoundError, TooManyRequestsError, UnauthorizedError,
)
from app.migrate import apply_migrations
from app.routers import auth, budgets, categories, dashboard, health, transactions

# Service errors -> HTTP status codes. Services raise these without knowing
# about HTTP; this table is the one place they are translated.
ERROR_STATUS = {
    NotFoundError: 404, InvalidInputError: 422, ConflictError: 409,
    UnauthorizedError: 401, TooManyRequestsError: 429,
}


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Tests pass their own settings (the budget_test database);
    the real server uses the settings from .env."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Startup: runs once, BEFORE the server accepts any request.
        # If either step fails, the server never starts (fail fast).
        active = settings or get_settings()
        # Locally the app migrates at startup. In production, leave
        # MIGRATION_DATABASE_URL out of the app's environment and run
        # `python -m app.migrate` as a deploy step instead, so the running
        # server never holds the owner's password.
        if active.migration_database_url:
            apply_migrations(active)
        db.open_pool(active)
        yield
        # Shutdown: runs once, when the server stops.
        db.close_pool()

    app = FastAPI(title="Budget App", lifespan=lifespan)
    for module in (health, auth, categories, transactions, budgets, dashboard):
        app.include_router(module.router)

    async def service_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=ERROR_STATUS[type(exc)], content={"detail": str(exc)})

    for error_type in ERROR_STATUS:
        app.add_exception_handler(error_type, service_error)

    @app.exception_handler(PoolTimeout)
    async def database_unavailable(request: Request, exc: PoolTimeout) -> JSONResponse:
        # No free database connection within the pool's wait time: a temporary
        # problem, so 503 (try again later) instead of a generic 500.
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable, please try again shortly."},
        )

    return app


app = create_app()
