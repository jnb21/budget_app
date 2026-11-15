from datetime import date

from app.errors import InvalidInputError, NotFoundError
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository

MAX_LIMIT_CENTS = 100_000_000  # $1,000,000


class BudgetService:
    def __init__(self, budgets: BudgetRepository, categories: CategoryRepository):
        self._budgets = budgets
        self._categories = categories

    def list_for_month(self, user_id: int, month: date) -> list[dict]:
        return self._budgets.list_for_month(user_id, month)

    def set(self, user_id: int, category_id: int, month: date, limit_cents: int) -> dict:
        """Create or replace the limit for this category and month."""
        if not 0 < limit_cents <= MAX_LIMIT_CENTS:
            raise InvalidInputError("limit must be more than $0 and at most $1,000,000")
        if self._categories.get_visible(user_id, category_id) is None:
            raise InvalidInputError("unknown category")
        return self._budgets.upsert(user_id, category_id, month.replace(day=1), limit_cents)

    def delete(self, user_id: int, budget_id: int) -> None:
        if not self._budgets.delete(user_id, budget_id):
            raise NotFoundError("budget not found")
