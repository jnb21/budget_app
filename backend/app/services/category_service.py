from app.errors import ConflictError, InvalidInputError, NotFoundError
from app.repositories.category_repository import CategoryRepository

MAX_NAME_LENGTH = 50


class CategoryService:
    def __init__(self, categories: CategoryRepository):
        self._categories = categories

    def list(self, user_id: int) -> list[dict]:
        return self._categories.list_visible(user_id)

    def create(self, user_id: int, name: str) -> dict:
        name = self._clean(name)
        if self._categories.name_taken(user_id, name):
            raise ConflictError(f"a category named {name!r} already exists")
        return self._categories.create(user_id, name)

    def rename(self, user_id: int, category_id: int, name: str) -> dict:
        self._own_category(user_id, category_id)
        name = self._clean(name)
        if self._categories.name_taken(user_id, name, except_id=category_id):
            raise ConflictError(f"a category named {name!r} already exists")
        return self._categories.rename_own(user_id, category_id, name)

    def delete(self, user_id: int, category_id: int) -> None:
        """Its transactions become uncategorized; its budgets are removed."""
        self._own_category(user_id, category_id)
        self._categories.delete_own(user_id, category_id)

    def _own_category(self, user_id: int, category_id: int) -> None:
        category = self._categories.get_visible(user_id, category_id)
        if category is None:
            raise NotFoundError("category not found")
        if category["is_default"]:
            raise InvalidInputError("default categories can't be renamed or deleted")

    @staticmethod
    def _clean(name: str) -> str:
        name = " ".join(name.split())  # trim and collapse inner spaces: "  Pet   food " -> "Pet food"
        if not 1 <= len(name) <= MAX_NAME_LENGTH:
            raise InvalidInputError(f"category name must be 1 to {MAX_NAME_LENGTH} characters")
        return name
