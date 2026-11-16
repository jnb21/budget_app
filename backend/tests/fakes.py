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

    def name_taken(self, user_id, name, except_id=None):
        return any(n.lower() == name.lower() and self._visible(user_id, cid) and cid != except_id
                   for cid, n in self.names.items())

    def rename_own(self, user_id, category_id, name):
        if self.owner.get(category_id) != user_id:
            return None
        self.names[category_id] = name
        return self._row(category_id)

    def delete_own(self, user_id, category_id):
        if self.owner.get(category_id) != user_id:
            return False
        del self.names[category_id], self.owner[category_id]
        return True

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


class FakeAuthRepository:
    """Users, sessions and failed logins in memory. `clock` decides what "now"
    is for session expiry, so tests can jump ahead in time."""

    def __init__(self, clock):
        self.clock = clock
        self.users = {}       # id -> {"id", "email", "password_hash"}
        self.sessions = {}    # token_hash -> (user_id, expires_at)
        self.failures = []    # (email, attempted_at)

    def find_user_by_email(self, email):
        return next((u for u in self.users.values() if u["email"].lower() == email.lower()), None)

    def get_user(self, user_id):
        return self.users.get(user_id)

    def create_user(self, email, password_hash):
        if self.find_user_by_email(email):
            return None
        user_id = len(self.users) + 1
        self.users[user_id] = {"id": user_id, "email": email, "password_hash": password_hash}
        return {"id": user_id, "email": email}

    def set_password_hash(self, user_id, password_hash):
        self.users[user_id]["password_hash"] = password_hash

    def delete_user(self, user_id):
        del self.users[user_id]
        self.sessions = {h: s for h, s in self.sessions.items() if s[0] != user_id}

    def create_session(self, token_hash, user_id, expires_at):
        self.sessions[token_hash] = (user_id, expires_at)

    def user_id_for_session(self, token_hash):
        user_id, expires_at = self.sessions.get(token_hash, (None, None))
        return user_id if user_id is not None and expires_at > self.clock() else None

    def delete_session(self, token_hash):
        self.sessions.pop(token_hash, None)

    def record_failure(self, email):
        self.failures.append((email, self.clock()))

    def recent_failures(self, email, since):
        return sum(1 for e, at in self.failures if e.lower() == email.lower() and at > since)

    def clear_failures(self, email):
        self.failures = [(e, at) for e, at in self.failures if e.lower() != email.lower()]

    def export_user_data(self, user_id):
        return {"account": {"id": user_id, "email": self.users[user_id]["email"]}}
