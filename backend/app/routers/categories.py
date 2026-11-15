from typing import Annotated

from fastapi import APIRouter, Depends, status
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
