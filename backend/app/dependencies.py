"""Builds services with their repositories, and says who the current user is.

Routers ask for these with Depends(...); tests replace them with
app.dependency_overrides. This is the only place routers' services get wired
to real repositories, so routers themselves import services only.
"""

from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.dashboard_service import DashboardService
from app.services.health_service import HealthService
from app.services.transaction_service import TransactionService

DEMO_USER_EMAIL = "demo@budget.local"


def get_current_user_id() -> int:
    """TEMPORARY, until login exists: every request acts as the demo user.

    When real login arrives, this function reads the session cookie instead.
    Nothing else changes: every route already gets its user_id from here.
    """
    return UserRepository().get_or_create(DEMO_USER_EMAIL)


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
