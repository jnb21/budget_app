"""Sign up, log in, log out, and the account itself (export, delete).

Passwords are hashed with argon2: slow on purpose, so guessing millions of
passwords from a stolen database is impractical. Sessions are random tokens;
the browser keeps the token in a cookie and the database keeps only its
SHA-256 hash.
"""

import functools
import hashlib
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.errors import ConflictError, InvalidInputError, TooManyRequestsError, UnauthorizedError
from app.repositories.auth_repository import AuthRepository

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128  # argon2 hashes everything: cap it so nobody can send megabytes
MAX_EMAIL_LENGTH = 254
MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(minutes=15)
WRONG_LOGIN = "wrong email or password"  # the same message whichever was wrong

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Long enough to pass the length rule, yet guessed first by every attacker.
# A real deployment should also check the HaveIBeenPwned breach list.
COMMON_PASSWORDS = frozenset({
    "1234567890", "12345678910", "0123456789", "1q2w3e4r5t", "1qaz2wsx3edc",
    "qwertyuiop", "qwerty1234", "qwerty12345", "asdfghjkl1", "zxcvbnm123",
    "password12", "password123", "password1!", "passw0rd123", "p@ssw0rd123",
    "iloveyou12", "iloveyou123", "welcome123", "letmein123", "abc1234567",
    "abcdefghij", "admin12345", "football123", "baseball123", "sunshine12",
    "princess12", "monkey12345", "dragon12345", "trustno1234", "changeme123",
})
_DEFAULT_HASHER = PasswordHasher()


@functools.cache
def _dummy_hash(hasher: PasswordHasher) -> str:
    """A hash to check against when the email doesn't exist, so a wrong email
    takes as long as a wrong password and the timing doesn't reveal which it
    was. Made once per hasher (hashing is slow on purpose: ~40 ms)."""
    return hasher.hash("not a real password, only for timing")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class LoggedIn:
    user: dict          # {"id", "email"}
    token: str          # goes in the cookie; never stored
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        hasher: PasswordHasher | None = None,
        session_days: int = 30,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self._repo = repository
        self._hasher = hasher or _DEFAULT_HASHER
        self._session_days = session_days
        self._now = now

    # --- Sign up / log in / log out ------------------------------------------

    def sign_up(self, email: str, password: str) -> LoggedIn:
        email = self._clean_email(email)
        self._check_password(password, email)
        user = self._repo.create_user(email, self._hasher.hash(password))
        if user is None:
            raise ConflictError("an account with this email already exists")
        return self._start_session(user)

    def log_in(self, email: str, password: str) -> LoggedIn:
        email = email.strip()
        if self._repo.recent_failures(email, self._now() - FAILURE_WINDOW) >= MAX_FAILURES:
            raise TooManyRequestsError("too many failed attempts; try again in 15 minutes")

        user = self._repo.find_user_by_email(email)
        stored_hash = user["password_hash"] if user and user["password_hash"] else _dummy_hash(self._hasher)
        if not self._verify(stored_hash, password) or user is None or not user["password_hash"]:
            self._repo.record_failure(email)
            raise UnauthorizedError(WRONG_LOGIN)

        self._repo.clear_failures(email)
        if self._hasher.check_needs_rehash(stored_hash):  # e.g. after argon2's settings get stronger
            self._repo.set_password_hash(user["id"], self._hasher.hash(password))
        return self._start_session(user)

    def log_out(self, token: str) -> None:
        self._repo.delete_session(hash_token(token))

    def user_id_for_token(self, token: str | None) -> int | None:
        if not token:
            return None
        return self._repo.user_id_for_session(hash_token(token))

    def me(self, user_id: int) -> dict:
        user = self._repo.get_user(user_id)
        return {"id": user["id"], "email": user["email"]}

    # --- The account ----------------------------------------------------------

    def set_password(self, user_id: int, password: str) -> None:
        user = self._repo.get_user(user_id)
        self._check_password(password, user["email"])
        self._repo.set_password_hash(user_id, self._hasher.hash(password))

    def delete_account(self, user_id: int, password: str) -> None:
        """Deletes the user and all their data. Needs the password again, so a
        borrowed laptop with an open session isn't enough."""
        user = self._repo.get_user(user_id)
        if not user["password_hash"] or not self._verify(user["password_hash"], password):
            raise InvalidInputError("wrong password")
        self._repo.delete_user(user_id)

    def export(self, user_id: int) -> dict:
        return self._repo.export_user_data(user_id)

    # --- Helpers --------------------------------------------------------------

    def _start_session(self, user: dict) -> LoggedIn:
        token = secrets.token_urlsafe(32)  # 256 random bits
        expires_at = self._now() + timedelta(days=self._session_days)
        self._repo.create_session(hash_token(token), user["id"], expires_at)
        return LoggedIn(user={"id": user["id"], "email": user["email"]}, token=token, expires_at=expires_at)

    def _verify(self, stored_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(stored_hash, password[:MAX_PASSWORD_LENGTH])
        except (VerificationError, InvalidHashError):
            return False

    @staticmethod
    def _clean_email(email: str) -> str:
        email = email.strip()
        if len(email) > MAX_EMAIL_LENGTH or not _EMAIL.match(email):
            raise InvalidInputError("enter a valid email address")
        return email

    @staticmethod
    def _check_password(password: str, email: str) -> None:
        """The same rules the sign-up form shows (frontend/src/passwordRules.js).
        Any character is accepted: letters in any language, spaces, symbols."""
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            raise InvalidInputError(
                f"password must be {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters"
            )
        if not any(ch.isalpha() for ch in password):
            raise InvalidInputError("password needs at least one letter")
        if all(ch.isalpha() for ch in password):  # needs a digit, a symbol or a space
            raise InvalidInputError("password needs at least one number, symbol or space")
        if password.lower() in COMMON_PASSWORDS:
            raise InvalidInputError("this password is too common; choose another")
        if password.strip().lower() == email.lower():
            raise InvalidInputError("password can't be your email")
