"""Business logic for the health check.

A service decides what results mean. It never writes SQL itself: it asks a
repository, which it receives from outside (dependency injection), so tests
can hand it a fake repository instead of a real database.
"""

import logging
from dataclasses import dataclass
from typing import Literal, Protocol

logger = logging.getLogger(__name__)


class PingsDatabase(Protocol):
    """What this service needs from a repository: just a ping() method.

    The real HealthRepository has one, and so can a fake in tests; neither
    has to inherit from anything (this is called structural typing).
    """

    def ping(self) -> None: ...


@dataclass(frozen=True)
class HealthStatus:
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


class HealthService:
    def __init__(self, repository: PingsDatabase):
        self._repository = repository

    def check(self) -> HealthStatus:
        """Report whether the app can reach its database.

        Any failure counts as "unavailable". The details go to the server log
        only, never into the status, because error messages can contain
        internals (host names, user names) that visitors must not see.
        """
        try:
            self._repository.ping()
        except Exception:
            logger.exception("health check: database did not answer")
            return HealthStatus(status="degraded", database="unavailable")
        return HealthStatus(status="ok", database="ok")
