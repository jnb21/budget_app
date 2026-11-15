"""Fake repositories shared by several test files: in-memory, no database."""

from dataclasses import asdict


class FakeHealthRepository:
    """Stands in for HealthRepository. Can pretend to work or to fail."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = 0

    def ping(self) -> None:
        self.calls += 1
        if self.error is not None:
            raise self.error


class FakeCategoryRepository:
    """Defaults are visible to everyone; `owned` maps category id -> owner user id."""

    def __init__(self, defaults=None, owned=None):
        self.names = dict(defaults or {1: "Groceries", 2: "Rent"})
        self.owner = {cid: None for cid in self.names}
        for cid, (name, user_id) in (owned or {}).items():
            self.names[cid], self.owner[cid] = name, user_id
        self.created = []

    def _visible(self, user_id, cid):
        return cid in self.names and self.owner[cid] in (None, user_id)

    def list_visible(self, user_id):
        return [self._row(cid) for cid in self.names if self._visible(user_id, cid)]

    def get_visible(self, user_id, category_id):
        return self._row(category_id) if self._visible(user_id, category_id) else None

    def name_taken(self, user_id, name):
        return any(n.lower() == name.lower() and self._visible(user_id, cid) for cid, n in self.names.items())

    def create(self, user_id, name):
        cid = max(self.names) + 1
        self.names[cid], self.owner[cid] = name, user_id
        self.created.append(name)
        return self._row(cid)

    def _row(self, cid):
        return {"id": cid, "name": self.names[cid], "is_default": self.owner[cid] is None}


class FakeTransactionRepository:
    """Keeps rows in a dict and, like the real one, only lets users touch their own."""

    def __init__(self):
        self.rows = {}  # id -> {"user_id": ..., **TransactionData fields}

    def create(self, user_id, data):
        new_id = len(self.rows) + 1
        self.rows[new_id] = {"id": new_id, "user_id": user_id, **asdict(data)}
        return self.rows[new_id]

    def update(self, user_id, transaction_id, data):
        row = self.rows.get(transaction_id)
        if row is None or row["user_id"] != user_id:
            return None
        row.update(asdict(data))
        return row

    def delete(self, user_id, transaction_id):
        row = self.rows.get(transaction_id)
        if row is None or row["user_id"] != user_id:
            return False
        del self.rows[transaction_id]
        return True


class FakeBudgetRepository:
    def __init__(self):
        self.saved = []  # (user_id, category_id, month, limit_cents)

    def upsert(self, user_id, category_id, month, limit_cents):
        self.saved.append((user_id, category_id, month, limit_cents))
        return {"user_id": user_id, "category_id": category_id, "month": month, "limit_cents": limit_cents}

    def delete(self, user_id, budget_id):
        return False
