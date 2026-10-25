from __future__ import annotations

import hashlib
import hmac
from base64 import urlsafe_b64encode
from secrets import compare_digest
from time import time

from argon2 import PasswordHasher
from fastapi import Depends, Request
from fastapi.security import HTTPBasic
from loguru import logger
from pydantic_yaml import parse_yaml_raw_as

from .schema import Page, PasswordMethod, User, UsersConfig

security = HTTPBasic(auto_error=False)
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


# The signed login of a user behind a password, under its path (docs/specs/login.md §3)
LOGIN_COOKIE = "yourss-login"


def login_signature(user: User, expiry: int) -> str:
    """HMAC of the user and the expiry, keyed by the stored password: changing it logs out every device (§4)."""
    if user.password is None:
        raise ValueError("Only a user behind a password logs in")
    key = hashlib.sha256(b"yourss-login|" + user.password.value.get_secret_value().encode()).digest()
    digest = hmac.new(key, f"{user.name}|{expiry}".encode(), hashlib.sha256).digest()
    return urlsafe_b64encode(digest).decode().rstrip("=")


def login_token(user: User, now: float | None = None) -> str:
    from .settings import current_config

    expiry = int((time() if now is None else now) + current_config.login_ttl.total_seconds())
    return f"{expiry}.{login_signature(user, expiry)}"


def check_login(user: User, token: str | None, now: float | None = None) -> bool:
    if user.password is None or not token:
        return False
    expiry, _, signature = token.partition(".")
    if not expiry.isdigit() or int(expiry) <= (time() if now is None else now):
        return False
    return compare_digest(signature.encode(), login_signature(user, int(expiry)).encode())


class LoginRequired(Exception):
    """A user behind a password without a valid login: the application answers the login form (see `main.py`)."""

    def __init__(self, user: User) -> None:
        super().__init__(user.name)
        self.user = user


class UnknownUser(Exception):
    """No user of this name: the application answers its 404 page (see `main.py`)."""


def find_user(username: str, config: UsersConfig | None = Depends(read_config)) -> User | None:
    return next((user for user in config.users if user.name == username), None) if config else None


def find_page(page: str, config: UsersConfig | None = Depends(read_config)) -> Page | None:
    """A visible page; a hidden one is only served inside a user."""
    found = config.page(page) if config else None
    return found if found is not None and found.visible else None


async def get_auth_user(request: Request, user: User | None = Depends(find_user)) -> User:
    """The user, once its login cookie or its Basic credentials are checked (docs/specs/login.md §5)."""
    if user is None:
        raise UnknownUser()

    if user.password is not None and not check_login(user, request.cookies.get(LOGIN_COOKIE)):
        credentials = await security(request)
        if credentials is None:
            raise LoginRequired(user)
        if not verify_password(user, credentials.password):
            logger.warning("Wrong Basic password for {} from {}", user.name, request.client and request.client.host)
            raise LoginRequired(user)

    return user
