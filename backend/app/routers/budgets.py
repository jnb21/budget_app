from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel

from app.dependencies import get_budget_service, get_current_user_id
from app.months import parse_month
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

UserId = Annotated[int, Depends(get_current_user_id)]
Service = Annotated[BudgetService, Depends(get_budget_service)]


class BudgetIn(BaseModel):
    category_id: int
    month: str  # "2026-11"
    limit_cents: int


class BudgetOut(BaseModel):
    id: int
    category_id: int
    category_name: str
    month: date
    limit_cents: int


@router.get("", response_model=list[BudgetOut])
def list_budgets(user_id: UserId, service: Service, month: Annotated[str, Query(examples=["2026-11"])]):
    return service.list_for_month(user_id, parse_month(month))


@router.put("", response_model=BudgetOut)
def set_budget(body: BudgetIn, user_id: UserId, service: Service):
    """Create the budget, or replace its limit if that category already has one this month."""
    return service.set(user_id, body.category_id, parse_month(body.month), body.limit_cents)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: int, user_id: UserId, service: Service):
    service.delete(user_id, budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
