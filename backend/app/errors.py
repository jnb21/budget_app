"""Errors that services raise. main.py turns each into an HTTP status code,
so services never need to know about HTTP."""


class NotFoundError(Exception):
    """It doesn't exist, or it belongs to another user (we don't say which). -> 404"""


class InvalidInputError(Exception):
    """The input breaks a business rule (e.g. an amount of zero). -> 422"""


class ConflictError(Exception):
    """It would duplicate something that must be unique. -> 409"""


class UnauthorizedError(Exception):
    """Not logged in, or wrong email/password. -> 401"""


class TooManyRequestsError(Exception):
    """Too many attempts or requests: wait and try again. -> 429"""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after  # seconds to wait; sent as the Retry-After header
