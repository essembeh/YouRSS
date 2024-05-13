from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAction(Enum):
    MODAL = "openModal"
    TAB = "openTab"
    EMBED = "openEmbedded"

    def __str__(self) -> str:
        return self.value


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"

    def __str__(self) -> str:
        return self.value


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YOURSS_")
    default_channels: str = "@JonnyGiger"
    redis_url: str | None = None
    ttl_metadata: int = 24 * 3600
    ttl_rss: int = 1 * 3600
    clean_titles: bool = False
    theme: Theme = Theme.LIGHT
    open_primary: OpenAction = OpenAction.MODAL
    open_secondary: OpenAction = OpenAction.TAB
    users_file: Path | None = None


class PasswordMethod(Enum):
    CLEAR = "clear"
    ARGON2 = "argon2"


class Password(BaseModel):
    method: PasswordMethod
    value: str


class User(BaseModel):
    name: str
    password: Password | None = None
    channels: list[str]
    theme: Theme | None = None


class UsersConfig(BaseModel):
    users: list[User]
