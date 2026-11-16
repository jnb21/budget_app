"""HTTP for login and the account: sets and clears the session cookie.

The cookie is httpOnly (JavaScript can't read it, so a malicious script
can't steal it), SameSite=Lax (other websites can't make the browser send it
with their POST/PUT/DELETE requests), and Secure in production (HTTPS only).
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from pydantic import BaseModel

from app.config import get_settings
from app.dependencies import (
    SESSION_COOKIE, get_auth_service, get_current_user_id, limit_delete_account, limit_login, limit_signup,
)
from app.services.auth_service import AuthService, LoggedIn

router = APIRouter(tags=["auth"])

Service = Annotated[AuthService, Depends(get_auth_service)]
UserId = Annotated[int, Depends(get_current_user_id)]


class Credentials(BaseModel):
    email: str
    password: str


class PasswordIn(BaseModel):
    password: str


class UserOut(BaseModel):
    id: int
    email: str


def _set_session_cookie(response: Response, logged_in: LoggedIn) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        logged_in.token,
        expires=logged_in.expires_at,
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax",
                           secure=get_settings().cookie_secure)


@router.post("/api/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(limit_signup)])
def sign_up(body: Credentials, response: Response, service: Service):
    logged_in = service.sign_up(body.email, body.password)
    _set_session_cookie(response, logged_in)
    return logged_in.user


@router.post("/api/auth/login", response_model=UserOut, dependencies=[Depends(limit_login)])
def log_in(body: Credentials, response: Response, service: Service):
    logged_in = service.log_in(body.email, body.password)
    _set_session_cookie(response, logged_in)
    return logged_in.user


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def log_out(service: Service, session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None):
    if session:
        service.log_out(session)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response


@router.get("/api/auth/me", response_model=UserOut)
def me(user_id: UserId, service: Service):
    return service.me(user_id)


@router.get("/api/account/export")
def export_my_data(user_id: UserId, service: Service):
    """Everything stored about you, as JSON (your right to your data)."""
    return service.export(user_id)


@router.post("/api/account/delete", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(limit_delete_account)])
def delete_my_account(body: PasswordIn, user_id: UserId, service: Service):
    """Deletes your account and all your data. Asks for the password again."""
    service.delete_account(user_id, body.password)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response
