from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel

from app.dependencies import get_current_user_id, get_transaction_service
from app.months import parse_month
from app.services.transaction_service import TransactionDraft, TransactionService

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

UserId = Annotated[int, Depends(get_current_user_id)]
Service = Annotated[TransactionService, Depends(get_transaction_service)]


class TransactionIn(BaseModel):
    posted_date: date
    amount_cents: int  # negative = spent, positive = received
    description: str
    category_id: int | None = None


class TransactionOut(BaseModel):
    id: int
    posted_date: date
    amount_cents: int
    description: str
    category_id: int | None
    category_name: str | None
    category_source: str


def _draft(body: TransactionIn) -> TransactionDraft:
    return TransactionDraft(**body.model_dump())


@router.get("", response_model=list[TransactionOut])
def list_transactions(user_id: UserId, service: Service, month: Annotated[str, Query(examples=["2026-11"])]):
    return service.list_for_month(user_id, parse_month(month))


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(body: TransactionIn, user_id: UserId, service: Service):
    return service.create(user_id, _draft(body))


@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(transaction_id: int, body: TransactionIn, user_id: UserId, service: Service):
    return service.update(user_id, transaction_id, _draft(body))


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, user_id: UserId, service: Service):
    service.delete(user_id, transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
