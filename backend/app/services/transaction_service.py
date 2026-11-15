from dataclasses import dataclass
from datetime import date

from app.errors import InvalidInputError, NotFoundError
from app.months import month_bounds
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionData, TransactionRepository

MAX_AMOUNT_CENTS = 100_000_000  # $1,000,000: anything bigger is almost surely a typo
MAX_DESCRIPTION_LENGTH = 200
EARLIEST_DATE = date(2000, 1, 1)


@dataclass(frozen=True)
class TransactionDraft:
    """What the user typed, before validation."""

    posted_date: date
    amount_cents: int
    description: str
    category_id: int | None = None


class TransactionService:
    def __init__(self, transactions: TransactionRepository, categories: CategoryRepository):
        self._transactions = transactions
        self._categories = categories

    def list_for_month(self, user_id: int, month: date) -> list[dict]:
        return self._transactions.list_between(user_id, *month_bounds(month))

    def create(self, user_id: int, draft: TransactionDraft) -> dict:
        return self._transactions.create(user_id, self._validate(user_id, draft))

    def update(self, user_id: int, transaction_id: int, draft: TransactionDraft) -> dict:
        updated = self._transactions.update(user_id, transaction_id, self._validate(user_id, draft))
        if updated is None:
            raise NotFoundError("transaction not found")
        return updated

    def delete(self, user_id: int, transaction_id: int) -> None:
        if not self._transactions.delete(user_id, transaction_id):
            raise NotFoundError("transaction not found")

    def _validate(self, user_id: int, draft: TransactionDraft) -> TransactionData:
        if draft.amount_cents == 0:
            raise InvalidInputError("amount can't be zero")
        if abs(draft.amount_cents) > MAX_AMOUNT_CENTS:
            raise InvalidInputError("amount is larger than $1,000,000")
        description = " ".join(draft.description.split())
        if not 1 <= len(description) <= MAX_DESCRIPTION_LENGTH:
            raise InvalidInputError(f"description must be 1 to {MAX_DESCRIPTION_LENGTH} characters")
        if draft.posted_date < EARLIEST_DATE:
            raise InvalidInputError("date must be in the year 2000 or later")
        # The category must be a default or one of THIS user's own: never another user's.
        if draft.category_id is not None and self._categories.get_visible(user_id, draft.category_id) is None:
            raise InvalidInputError("unknown category")
        return TransactionData(
            posted_date=draft.posted_date,
            amount_cents=draft.amount_cents,
            description=description,
            category_id=draft.category_id,
            category_source="user" if draft.category_id is not None else "none",
        )
