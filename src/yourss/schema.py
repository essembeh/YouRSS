from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
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
    # Disk cache of the feeds and channel metadata (docs/specs/disk-cache.md), off by default; a temporary folder when
    # none is given
    cache_enabled: bool = False
    cache_folder: Path | None = None
    # A cached feed younger than the TTL is served without asking Youtube
    cache_rss_ttl: timedelta = timedelta(minutes=30)
    # When the fetch fails, a cached feed younger than this is served instead of the error
    cache_rss_fallback_ttl: timedelta = timedelta(hours=48)
    # A cached channel description younger than this is served without scraping Youtube
    cache_metadata_ttl: timedelta = timedelta(days=7)
    # Refresh the feeds of every page in the background, a round every cache_rss_ttl minus a minute
    warmup_enabled: bool = False
    # How long the login of a user behind a password lasts in a browser (docs/specs/login.md §8)
    login_ttl: timedelta = timedelta(days=90)

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


# Channel ids, handles and playlist ids, at least one
Channels = Annotated[list[str], Field(min_length=1)]
# A page or user name: in the URL (`/p/<page>`, `/u/<user>/<page>`), a DOM id, a Secret key in the chart
Name = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")]


class Page(BaseModel):
    """A page of a user, its folder `/u/<user>/<name>`; with `publish`, it is also served at `/p/<publish>`."""

    # Unknown keys are refused: a typo on `publish` must not leave a page unpublished, or the reverse
    model_config = ConfigDict(extra="forbid")

    name: Name
    # The name of the page at `/p/<publish>`, unique across the users
    publish: Name | None = None
    channels: Channels


class User(BaseModel):
    """A user holds pages, its folders (`/u/<name>/<page>`); its password protects them all, not their public copy."""

    model_config = ConfigDict(extra="forbid")

    name: Name
    password: Password | None = None
    pages: Annotated[list[Page], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_pages(self) -> Self:
        names = [page.name for page in self.pages]
        if len(set(names)) != len(names):
            raise ValueError("the pages of a user have distinct names")
        return self

    def page(self, name: str) -> Page | None:
        return next((page for page in self.pages if page.name == name), None)


class UsersConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    users: list[User] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_names(self) -> Self:
        users = [user.name for user in self.users]
        if len(set(users)) != len(users):
            raise ValueError("the users have distinct names")
        published = [page.publish for page in self.pages if page.publish is not None]
        if len(set(published)) != len(published):
            raise ValueError("the published pages have distinct names")
        return self

    @property
    def pages(self) -> list[Page]:
        """Every page, user after user."""
        return [page for user in self.users for page in user.pages]

    def public_page(self, name: str) -> Page | None:
        return next((page for page in self.pages if page.publish == name), None)
