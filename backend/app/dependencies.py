"""Builds services with their repositories, and says who the current user is.

Routers ask for these with Depends(...); tests replace them with
app.dependency_overrides. This is the only place routers' services get wired
to real repositories, so routers themselves import services only.
"""

from typing import Annotated

from fastapi import Cookie, Depends

from app.config import get_settings
from app.errors import UnauthorizedError
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


def get_current_user_id(
    auth: Annotated[AuthService, Depends(get_auth_service)],
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> int:
    """The logged-in user, from the session cookie. 401 if there isn't one.

    Every route that touches user data gets its user_id from here, so this is
    the one place that decides who is asking.
    """
    user_id = auth.user_id_for_token(session)
    if user_id is None:
        raise UnauthorizedError("please log in")
    return user_id


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
