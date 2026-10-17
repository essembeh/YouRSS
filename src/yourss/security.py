from __future__ import annotations

from secrets import compare_digest

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic
from loguru import logger
from pydantic_yaml import parse_yaml_raw_as
from starlette.status import HTTP_401_UNAUTHORIZED

from .schema import Page, PasswordMethod, User, UsersConfig

security = HTTPBasic()
argon2hasher = PasswordHasher()


def verify_password(user: User, value: str) -> bool:
    if user.password is None:
        return False
    if user.password.method == PasswordMethod.CLEAR:
        # Bytes, not str: compare_digest refuses non-ASCII strings
        return compare_digest(user.password.value.get_secret_value().encode(), value.encode())
    if user.password.method == PasswordMethod.ARGON2:
        try:
            return argon2hasher.verify(user.password.value.get_secret_value(), value)
        except Exception:
            return False

    raise ValueError("Invalid password method")


def read_config() -> UsersConfig | None:
    """The pages and users file; none without a file or when it cannot be read."""
    from .settings import current_config

    if current_config.users_file is None or not current_config.users_file.exists():
        return None
    try:
        return parse_yaml_raw_as(UsersConfig, current_config.users_file.read_bytes())
    except Exception as error:
        logger.exception(error)
        return None


class UnknownUser(Exception):
    """No user of this name: the application answers its 404 page (see `main.py`)."""


def find_user(username: str, config: UsersConfig | None = Depends(read_config)) -> User | None:
    return next((user for user in config.users if user.name == username), None) if config else None


def find_page(page: str, config: UsersConfig | None = Depends(read_config)) -> Page | None:
    """A visible page; a hidden one is only served inside a user."""
    found = config.page(page) if config else None
    return found if found is not None and found.visible else None


async def get_auth_user(request: Request, user: User | None = Depends(find_user)) -> User:
    """
    See https://fastapi.tiangolo.com/advanced/security/http-basic-auth/
    """
    if user is None:
        raise UnknownUser()

    if user.password is not None:
        logger.debug("User needs a password: {}", user.name)
        if (credentials := await security(request)) is None:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing credentials")
        if not verify_password(user, credentials.password):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return user
