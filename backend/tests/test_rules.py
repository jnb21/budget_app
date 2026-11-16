"""Unit tests for the business rules in the category, transaction and budget
services, using in-memory fakes (tests/fakes.py) instead of the database."""

from datetime import date

import pytest

from app.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionDraft, TransactionService
from tests.fakes import FakeBudgetRepository, FakeCategoryRepository, FakeTransactionRepository

ALICE, BOB = 1, 2


def transaction_service(categories=None):
    return TransactionService(FakeTransactionRepository(), categories or FakeCategoryRepository())


def draft(**changes):
    values = {"posted_date": date(2026, 11, 3), "amount_cents": -1_250, "description": "Coffee", "category_id": 1}
    return TransactionDraft(**{**values, **changes})


# --- Transactions -------------------------------------------------------------

def test_a_valid_transaction_is_saved_with_source_user():
    saved = transaction_service().create(ALICE, draft())

    assert (saved["amount_cents"], saved["category_id"], saved["category_source"]) == (-1_250, 1, "user")


def test_no_category_means_source_none():
    assert transaction_service().create(ALICE, draft(category_id=None))["category_source"] == "none"


def test_description_spaces_are_cleaned_up():
    assert transaction_service().create(ALICE, draft(description="  Pizza   night "))["description"] == "Pizza night"


@pytest.mark.parametrize("changes, message", [
    ({"amount_cents": 0}, "zero"),
    ({"amount_cents": 100_000_001}, "1,000,000"),
    ({"amount_cents": -100_000_001}, "1,000,000"),
    ({"description": "   "}, "description"),
    ({"description": "x" * 201}, "description"),
    ({"posted_date": date(1999, 12, 31)}, "2000"),
    ({"category_id": 999}, "unknown category"),
])
def test_invalid_transactions_are_refused(changes, message):
    with pytest.raises(InvalidInputError, match=message):
        transaction_service().create(ALICE, draft(**changes))


def test_largest_allowed_amount_is_accepted():
    # Boundary: exactly $1,000,000 is fine; one cent more is not (above).
    transaction_service().create(ALICE, draft(amount_cents=-100_000_000))


def test_another_users_category_cannot_be_used():
    categories = FakeCategoryRepository(owned={50: ("Bob's pets", BOB)})

    with pytest.raises(InvalidInputError, match="unknown category"):
        transaction_service(categories).create(ALICE, draft(category_id=50))


def test_updating_or_deleting_someone_elses_transaction_is_not_found():
    service = transaction_service()
    bobs = service.create(BOB, draft())

    with pytest.raises(NotFoundError):
        service.update(ALICE, bobs["id"], draft(amount_cents=-1))
    with pytest.raises(NotFoundError):
        service.delete(ALICE, bobs["id"])


# --- Categories ---------------------------------------------------------------

def test_a_new_category_name_is_cleaned_and_saved():
    repo = FakeCategoryRepository()

    created = CategoryService(repo).create(ALICE, "  Pet   food ")

    assert created["name"] == "Pet food"
    assert created["is_default"] is False


def test_a_name_that_matches_a_default_is_a_conflict():
    with pytest.raises(ConflictError):
        CategoryService(FakeCategoryRepository()).create(ALICE, "groceries")


def test_bobs_category_name_is_free_for_alice():
    repo = FakeCategoryRepository(owned={50: ("Pets", BOB)})

    CategoryService(repo).create(ALICE, "Pets")

    assert repo.created == ["Pets"]


@pytest.mark.parametrize("bad", ["", "    ", "x" * 51])
def test_bad_category_names_are_refused(bad):
    with pytest.raises(InvalidInputError):
        CategoryService(FakeCategoryRepository()).create(ALICE, bad)


# --- Budgets ------------------------------------------------------------------

@pytest.mark.parametrize("limit", [0, -500, 100_000_001])
def test_budget_limit_must_be_positive_and_sensible(limit):
    with pytest.raises(InvalidInputError):
        BudgetService(FakeBudgetRepository(), FakeCategoryRepository()).set(ALICE, 1, date(2026, 11, 1), limit)


def test_budget_on_an_unknown_category_is_refused():
    with pytest.raises(InvalidInputError, match="unknown category"):
        BudgetService(FakeBudgetRepository(), FakeCategoryRepository()).set(ALICE, 999, date(2026, 11, 1), 10_000)


def test_budget_month_is_stored_as_its_first_day():
    budgets = FakeBudgetRepository()

    BudgetService(budgets, FakeCategoryRepository()).set(ALICE, 1, date(2026, 11, 17), 10_000)

    assert budgets.saved == [(ALICE, 1, date(2026, 11, 1), 10_000)]


def test_renaming_a_category_cleans_the_name():
    repo = FakeCategoryRepository(owned={50: ("Pets", ALICE)})

    renamed = CategoryService(repo).rename(ALICE, 50, "  Pet   care ")

    assert renamed["name"] == "Pet care"


def test_a_category_can_be_renamed_to_a_new_case_of_its_own_name():
    repo = FakeCategoryRepository(owned={50: ("Pets", ALICE)})

    assert CategoryService(repo).rename(ALICE, 50, "PETS")["name"] == "PETS"


@pytest.mark.parametrize("action", ["rename", "delete"])
def test_defaults_cannot_be_renamed_or_deleted(action):
    service = CategoryService(FakeCategoryRepository())
    args = (ALICE, 1, "Food") if action == "rename" else (ALICE, 1)

    with pytest.raises(InvalidInputError, match="default"):
        getattr(service, action)(*args)


@pytest.mark.parametrize("action", ["rename", "delete"])
def test_someone_elses_category_is_not_found(action):
    service = CategoryService(FakeCategoryRepository(owned={50: ("Pets", BOB)}))
    args = (ALICE, 50, "Mine") if action == "rename" else (ALICE, 50)

    with pytest.raises(NotFoundError):
        getattr(service, action)(*args)
