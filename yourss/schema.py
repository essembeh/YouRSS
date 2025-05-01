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
    clean_titles: bool = False
    theme: Theme = Theme.LIGHT
    open_primary: OpenAction = OpenAction.MODAL
    open_secondary: OpenAction = OpenAction.TAB
    users_file: Path | None = None
    player_url: str = r"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1"

    def get_player_url(self, video_id: str) -> str:
        return self.player_url.format(video_id=video_id)


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
