from app.errors import ConflictError, InvalidInputError
from app.repositories.category_repository import CategoryRepository

MAX_NAME_LENGTH = 50


class CategoryService:
    def __init__(self, categories: CategoryRepository):
        self._categories = categories

    def list(self, user_id: int) -> list[dict]:
        return self._categories.list_visible(user_id)

    def create(self, user_id: int, name: str) -> dict:
        name = " ".join(name.split())  # trim and collapse inner spaces: "  Pet   food " -> "Pet food"
        if not 1 <= len(name) <= MAX_NAME_LENGTH:
            raise InvalidInputError(f"category name must be 1 to {MAX_NAME_LENGTH} characters")
        if self._categories.name_taken(user_id, name):
            raise ConflictError(f"a category named {name!r} already exists")
        return self._categories.create(user_id, name)
