from __future__ import annotations

from typing import Optional

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic
from loguru import logger
from pydantic_yaml import parse_yaml_raw_as
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from .schema import PasswordMethod, User, UsersConfig

security = HTTPBasic()
argon2hasher = PasswordHasher()


def verify_password(user: User, value: str) -> bool:
    if user.password is None:
        return False
    if user.password.method == PasswordMethod.CLEAR:
        return user.password.value == value
    if user.password.method == PasswordMethod.ARGON2:
        try:
            return argon2hasher.verify(user.password.value, value)
        except BaseException:
            return False

    raise ValueError("Invalid password method")


def find_user(username: str) -> Optional[User]:
    from .settings import current_config

    if current_config.users_file is not None and current_config.users_file.exists():
        try:
            config = parse_yaml_raw_as(
                UsersConfig, current_config.users_file.read_bytes()
            )
            for user in config.users:
                if user.name == username:
                    return user
        except BaseException as error:
            logger.exception(error)


async def get_auth_user(
    request: Request, user: User | None = Depends(find_user)
) -> User:
    """
    See https://fastapi.tiangolo.com/advanced/security/http-basic-auth/
    """
    if user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    if user.password is not None:
        logger.debug("User needs a password: {}", user.name)
        if (credentials := await security(request)) is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Missing credentials"
            )
        if not verify_password(user, credentials.password):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

    return user
