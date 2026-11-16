"""Builds services with their repositories, and says who the current user is.

Routers ask for these with Depends(...); tests replace them with
app.dependency_overrides. This is the only place routers' services get wired
to real repositories, so routers themselves import services only.

The rate limits (app/rate_limit.py) are dependencies too: a route that
depends on limit_login, for example, takes a token before it runs.
"""

from typing import Annotated

from fastapi import Cookie, Depends, Request

from app.config import get_settings
from app.errors import UnauthorizedError
from app.rate_limit import API, DELETE_ACCOUNT, LOGIN, SIGNUP, TokenBucketLimiter, client_key
from app.repositories.auth_repository import AuthRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.auth_service import AuthService
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.dashboard_service import DashboardService
from app.services.health_service import HealthService
from app.services.transaction_service import TransactionService

DEMO_USER_EMAIL = "demo@budget.local"  # the fake-data user (see app/seed.py)
SESSION_COOKIE = "session"


def get_auth_service() -> AuthService:
    return AuthService(AuthRepository(), session_days=get_settings().session_days)


def get_optional_user_id(
    auth: Annotated[AuthService, Depends(get_auth_service)],
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> int | None:
    """The logged-in user from the session cookie, or None. FastAPI runs this
    once per request even when several dependencies ask for it."""
    return auth.user_id_for_token(session)


def get_current_user_id(user_id: Annotated[int | None, Depends(get_optional_user_id)]) -> int:
    """The logged-in user. 401 if there isn't one.

    Every route that touches user data gets its user_id from here, so this is
    the one place that decides who is asking.
    """
    if user_id is None:
        raise UnauthorizedError("please log in")
    return user_id


# --- Rate limits ------------------------------------------------------------------

def _limiter(request: Request) -> TokenBucketLimiter:
    return request.app.state.limiter


def limit_api(request: Request, user_id: Annotated[int | None, Depends(get_optional_user_id)]) -> None:
    """Every /api request: counted per user when logged in (so people sharing
    one IP, like an office, don't share a bucket), per IP otherwise."""
    who = f"user:{user_id}" if user_id is not None else client_key(request.client and request.client.host)
    _limiter(request).take(API, who)


def limit_login(request: Request) -> None:
    _limiter(request).take(LOGIN, client_key(request.client and request.client.host))


def limit_signup(request: Request) -> None:
    _limiter(request).take(SIGNUP, client_key(request.client and request.client.host))


def limit_delete_account(request: Request, user_id: Annotated[int, Depends(get_current_user_id)]) -> None:
    _limiter(request).take(DELETE_ACCOUNT, f"user:{user_id}")


def get_health_service() -> HealthService:
    return HealthService(repository=HealthRepository())


def get_category_service() -> CategoryService:
    return CategoryService(CategoryRepository())


def get_transaction_service() -> TransactionService:
    return TransactionService(TransactionRepository(), CategoryRepository())


def get_budget_service() -> BudgetService:
    return BudgetService(BudgetRepository(), CategoryRepository())


def get_dashboard_service() -> DashboardService:
    return DashboardService(TransactionRepository(), BudgetRepository())
