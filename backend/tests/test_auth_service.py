"""Unit tests for the login rules (AuthService), with an in-memory repository,
a fake clock, and a FAST password hasher (argon2's real settings take ~40 ms
per hash on purpose; tests would crawl)."""

from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher

from app.errors import ConflictError, InvalidInputError, TooManyRequestsError, UnauthorizedError
from app.services.auth_service import MAX_FAILURES, WRONG_LOGIN, AuthService, hash_token
from tests.fakes import FakeAuthRepository

FAST = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
PASSWORD = "correct horse battery"


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def repo(clock):
    return FakeAuthRepository(clock)


@pytest.fixture
def auth(repo, clock):
    return AuthService(repo, hasher=FAST, session_days=30, now=clock)


# --- Sign up --------------------------------------------------------------------

def test_sign_up_logs_you_in(auth):
    logged_in = auth.sign_up("alice@example.com", PASSWORD)

    assert logged_in.user == {"id": 1, "email": "alice@example.com"}
    assert auth.user_id_for_token(logged_in.token) == 1


def test_the_password_is_stored_hashed_never_as_is(auth, repo):
    auth.sign_up("alice@example.com", PASSWORD)

    stored = repo.users[1]["password_hash"]
    assert PASSWORD not in stored
    assert stored.startswith("$argon2id$")


def test_only_a_hash_of_the_session_token_is_stored(auth, repo):
    logged_in = auth.sign_up("alice@example.com", PASSWORD)

    assert logged_in.token not in repo.sessions
    assert hash_token(logged_in.token) in repo.sessions


def test_each_login_gets_a_different_token(auth):
    first = auth.sign_up("alice@example.com", PASSWORD).token
    second = auth.log_in("alice@example.com", PASSWORD).token

    assert first != second


@pytest.mark.parametrize("email", ["", "alice", "alice@", "@example.com", "alice@example", "a b@example.com",
                                   "x" * 250 + "@example.com"])
def test_invalid_emails_are_refused(auth, email):
    with pytest.raises(InvalidInputError, match="valid email"):
        auth.sign_up(email, PASSWORD)


@pytest.mark.parametrize("password, message", [
    ("short1", "10 to 128"),
    ("abcdefgh1", "10 to 128"),           # one short of the minimum
    ("a" * 128 + "1", "10 to 128"),       # one over the maximum
    ("abcdefghijk", "number, symbol or space"),
    ("Ünïcödéonly", "number, symbol or space"),
    ("1234567890!", "at least one letter"),
    ("!!!!--....__", "at least one letter"),
    ("Password123", "too common"),        # capitals don't help
    ("alice@example.com", "can't be your email"),
])
def test_weak_passwords_are_refused(auth, password, message):
    with pytest.raises(InvalidInputError, match=message):
        auth.sign_up("alice@example.com", password)


@pytest.mark.parametrize("password", [
    "abcdefgh12",                 # exactly 10
    "a" * 127 + "1",              # exactly 128
    "correct horse battery",      # a passphrase: the spaces count
    "mot de passe très sûr",      # accents and spaces
    "пароль-надёжный",            # any alphabet
    "ab😀cdefghij",                # an emoji counts as a symbol
])
def test_good_passwords_with_any_characters_are_accepted(auth, password):
    auth.sign_up("alice@example.com", password)


def test_the_same_email_twice_is_a_conflict_whatever_the_case(auth):
    auth.sign_up("alice@example.com", PASSWORD)

    with pytest.raises(ConflictError):
        auth.sign_up("ALICE@example.com", PASSWORD)


# --- Log in ---------------------------------------------------------------------

def test_wrong_password_and_unknown_email_get_the_same_answer(auth):
    auth.sign_up("alice@example.com", PASSWORD)

    with pytest.raises(UnauthorizedError) as wrong_password:
        auth.log_in("alice@example.com", "not the password")
    with pytest.raises(UnauthorizedError) as unknown_email:
        auth.log_in("nobody@example.com", PASSWORD)

    assert str(wrong_password.value) == str(unknown_email.value) == WRONG_LOGIN


def test_a_user_without_a_password_cannot_log_in(auth, repo):
    repo.users[7] = {"id": 7, "email": "old@example.com", "password_hash": None}

    with pytest.raises(UnauthorizedError):
        auth.log_in("old@example.com", "")


def test_too_many_failures_block_even_the_right_password(auth):
    auth.sign_up("alice@example.com", PASSWORD)
    for _ in range(MAX_FAILURES):
        with pytest.raises(UnauthorizedError):
            auth.log_in("alice@example.com", "guess")

    with pytest.raises(TooManyRequestsError):
        auth.log_in("alice@example.com", PASSWORD)


def test_the_block_lifts_after_15_minutes(auth, clock):
    auth.sign_up("alice@example.com", PASSWORD)
    for _ in range(MAX_FAILURES):
        with pytest.raises(UnauthorizedError):
            auth.log_in("alice@example.com", "guess")

    clock.now += timedelta(minutes=16)

    assert auth.log_in("alice@example.com", PASSWORD).user["id"] == 1


def test_a_successful_login_resets_the_failure_count(auth, repo):
    auth.sign_up("alice@example.com", PASSWORD)
    with pytest.raises(UnauthorizedError):
        auth.log_in("alice@example.com", "guess")

    auth.log_in("alice@example.com", PASSWORD)

    assert repo.failures == []


def test_an_old_hash_is_upgraded_when_argon2_settings_get_stronger(repo, clock):
    AuthService(repo, hasher=FAST, now=clock).sign_up("alice@example.com", PASSWORD)
    stronger = PasswordHasher(time_cost=2, memory_cost=16, parallelism=1)

    AuthService(repo, hasher=stronger, now=clock).log_in("alice@example.com", PASSWORD)

    assert not stronger.check_needs_rehash(repo.users[1]["password_hash"])


# --- Sessions -------------------------------------------------------------------

def test_a_session_expires_after_30_days(auth, clock):
    token = auth.sign_up("alice@example.com", PASSWORD).token

    clock.now += timedelta(days=29)
    assert auth.user_id_for_token(token) == 1
    clock.now += timedelta(days=2)
    assert auth.user_id_for_token(token) is None


def test_logging_out_ends_the_session_immediately(auth):
    token = auth.sign_up("alice@example.com", PASSWORD).token

    auth.log_out(token)

    assert auth.user_id_for_token(token) is None


@pytest.mark.parametrize("token", [None, "", "made-up-token"])
def test_no_or_unknown_token_means_nobody(auth, token):
    assert auth.user_id_for_token(token) is None


# --- The account ----------------------------------------------------------------

def test_deleting_the_account_needs_the_right_password(auth, repo):
    auth.sign_up("alice@example.com", PASSWORD)

    with pytest.raises(InvalidInputError, match="wrong password"):
        auth.delete_account(1, "not the password")
    assert 1 in repo.users

    auth.delete_account(1, PASSWORD)
    assert 1 not in repo.users
