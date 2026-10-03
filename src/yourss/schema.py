from datetime import timedelta
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Every setting is a YOURSS_<NAME> environment variable (see the README and the Helm values)."""

    model_config = SettingsConfigDict(env_prefix="YOURSS_")

    # Channels of the home page, comma separated
    default_channels: str = "@JonnyGiger"
    # Serve the generated API documentation (/docs, /redoc, /openapi.json); off outside development
    api_docs_enabled: bool = False
    # YAML file declaring the user pages
    users_file: Path | None = None
    # Capitalize the titles to tame UPPERCASE ones
    clean_titles: bool = False
    # RSS fallback on disk for Youtube's transient 404: folder (unset disables) and max age
    cache_folder: Path | None = None
    cache_max_age: timedelta = timedelta(hours=24)
    # In-memory cache of channel names and avatars, 0 disables it
    channel_cache_ttl: timedelta = timedelta(hours=1)


class PasswordMethod(Enum):
    CLEAR = "clear"
    ARGON2 = "argon2"


class Password(BaseModel):
    method: PasswordMethod
    value: SecretStr


class User(BaseModel):
    name: str
    password: Password | None = None
    channels: list[str] = Field(min_length=1)


class UsersConfig(BaseModel):
    users: list[User] = Field(min_length=1)
