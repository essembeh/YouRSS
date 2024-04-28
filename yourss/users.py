from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic
from loguru import logger
from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

security = HTTPBasic()
argon2hasher = PasswordHasher()


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"

    def __str__(self) -> str:
        return self.value


class PasswordMethod(Enum):
    CLEAR = "clear"
    ARGON2 = "argon2"


class Password(BaseModel):
    method: PasswordMethod
    value: str

    def verify_password(self, password: str) -> bool:
        if password is None:
            return False
        if self.method == PasswordMethod.CLEAR:
            return self.value == password
        if self.method == PasswordMethod.ARGON2:
            try:
                return argon2hasher.verify(self.value, password)
            except BaseException:
                return False

        raise ValueError("Invalid password method")


class User(BaseModel):
    name: str
    password: Password | None = None
    channels: list[str]
    theme: Theme | None = None


class Config(BaseModel):
    users: list[User]


def find_user(username: str) -> Optional[User]:
    from .config import current_config

    if (user_yaml := current_config.USERS_FILE) is not None:
        try:
            config = parse_yaml_raw_as(Config, Path(user_yaml).read_bytes())
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
        if not user.password.verify_password(credentials.password):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

    return user
