from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
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
    clean_titles: bool = False
    theme: Theme = Theme.LIGHT
    open_primary: OpenAction = OpenAction.MODAL
    open_secondary: OpenAction = OpenAction.TAB
    users_file: Optional[Path] = None
    player_nocookie: bool = True
    custom_lang: Optional[str] = None

    @property
    def custom_langs(self) -> Optional[List[str]]:
        return self.custom_lang.split() if self.custom_lang else None


class PasswordMethod(Enum):
    CLEAR = "clear"
    ARGON2 = "argon2"


class Password(BaseModel):
    method: PasswordMethod
    value: str


class User(BaseModel):
    name: str
    password: Optional[Password] = None
    channels: list[str] = Field(min_length=1)
    theme: Optional[Theme] = None


class UsersConfig(BaseModel):
    users: list[User] = Field(min_length=1)
