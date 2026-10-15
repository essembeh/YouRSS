from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Every setting is a YOURSS_<NAME> environment variable (see the README and the Helm values)."""

    model_config = SettingsConfigDict(env_prefix="YOURSS_")

    # Let visitors build their own multi channel page; off, only user and channel pages remain
    custom_pages_enabled: bool = True
    # How many channels and playlists the address of a custom page may hold
    max_page_items: int = Field(default=12, ge=1)
    # Serve the generated API documentation (/docs, /redoc, /openapi.json); off outside development
    api_docs_enabled: bool = False
    # YAML file declaring the user pages
    users_file: Path | None = None
    # Capitalize the titles to tame UPPERCASE ones
    clean_titles: bool = False
    # Disk cache of the feeds and channel metadata (docs/specs/disk-cache.md), a temporary folder when none is given
    cache_enabled: bool = True
    cache_folder: Path | None = None
    # A cached feed younger than the TTL is served without asking Youtube
    cache_rss_ttl: timedelta = timedelta(minutes=30)
    # When the fetch fails, a cached feed younger than this is served instead of the error
    cache_rss_fallback_ttl: timedelta = timedelta(hours=48)
    # A cached channel description younger than this is served without scraping Youtube
    cache_metadata_ttl: timedelta = timedelta(days=7)

    @model_validator(mode="after")
    def _check_cache_ttls(self) -> Self:
        if self.cache_rss_ttl > self.cache_rss_fallback_ttl:
            raise ValueError("cache_rss_ttl must not exceed cache_rss_fallback_ttl")
        return self


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
