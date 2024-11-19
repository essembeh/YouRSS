import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Self
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from httpx import Response

from .model import (
    BrowseData,
    ChannelDescription,
)
from .utils import is_channel_id, json_first

YTCFG_PATTERN = r"ytcfg\.set\((?P<json>(?:\"[^\"]*\"|'[^']*'|[^()])*)\)"
YTINITIALDATA_PATTERN = r"ytInitialData = (?P<json>{.*?});"
ALLOWED_HOSTS = ["www.youtube.com", "youtube.com", "youtu.be"]


@dataclass
class PageScrapper:
    soup: BeautifulSoup

    @classmethod
    def from_response(cls, resp: Response) -> Self:
        resp.raise_for_status()
        return cls(soup=BeautifulSoup(resp.text, features="html.parser"))

    def get_metadata(self) -> ChannelDescription:
        meta = {
            m["property"]: m.get("content")
            for m in self.soup.find_all("meta")
            if "property" in m.attrs
        }
        name = meta["og:title"]
        avatar = meta.get("og:image")
        home = meta["og:url"]
        url = urlparse(home)
        assert url.hostname in ALLOWED_HOSTS, f"Not a valid youtube url: {home}"
        assert is_channel_id(
            channel_id := url.path.split("/")[-1]
        ), f"Invalid channel_id: {channel_id}"

        return ChannelDescription(
            channel_id=channel_id, name=name, avatar=avatar, home=home
        )

    def _iter_scripts(self) -> Iterator[str]:
        for script in self.soup.find_all("script"):
            if script.string is not None:
                yield script.string

    def find_browse_data(self) -> BrowseData | None:
        for script in self._iter_scripts():
            if (m := re.search(YTINITIALDATA_PATTERN, script, re.DOTALL)) is not None:
                return BrowseData.from_json_string(m.group("json"))

    def find_client_data(self) -> Dict[str, Any] | None:
        for script in self._iter_scripts():
            if (
                "INNERTUBE_CONTEXT" in script
                and (m := re.search(YTCFG_PATTERN, script, re.DOTALL)) is not None
            ):
                payload = json.loads(m.group("json"))
                return json_first("$.INNERTUBE_CONTEXT.client", payload)
