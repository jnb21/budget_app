from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user_id, get_dashboard_service
from app.months import parse_month
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class CategoryLine(BaseModel):
    category_id: int | None
    category_name: str
    spent_cents: int
    limit_cents: int | None
    remaining_cents: int | None
    percent_used: int | None
    status: Literal["ok", "near", "over", "no_budget"]


class DashboardOut(BaseModel):
    month: str
    income_cents: int
    spent_cents: int
    net_cents: int
    budgeted_cents: int
    categories: list[CategoryLine]


@router.get("", response_model=DashboardOut)
def get_dashboard(
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    month: Annotated[str, Query(examples=["2026-11"])],
):
    return service.summary(user_id, parse_month(month))
