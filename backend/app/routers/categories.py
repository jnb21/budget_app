from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.dependencies import get_category_service, get_current_user_id
from app.services.category_service import CategoryService

router = APIRouter(prefix="/api/categories", tags=["categories"])

UserId = Annotated[int, Depends(get_current_user_id)]
Service = Annotated[CategoryService, Depends(get_category_service)]


class CategoryIn(BaseModel):
    name: str


class CategoryOut(BaseModel):
    id: int
    name: str
    is_default: bool


@router.get("", response_model=list[CategoryOut])
def list_categories(user_id: UserId, service: Service):
    return service.list(user_id)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryIn, user_id: UserId, service: Service):
    return service.create(user_id, body.name)


@router.put("/{category_id}", response_model=CategoryOut)
def rename_category(category_id: int, body: CategoryIn, user_id: UserId, service: Service):
    return service.rename(user_id, category_id, body.name)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, user_id: UserId, service: Service):
    """Its transactions become uncategorized; its budgets are removed."""
    service.delete(user_id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
