from typing import Any, Dict, List
from urllib.parse import urlencode

from ..youtube.model import BrowseData


def force_https(url: str) -> str:
    assert isinstance(url, str)
    if url.startswith("http:"):
        return url.replace("http:", "https:", 1)
    return url


def parse_channel_names(text: str, delimiter: str = ",") -> List[str]:
    return list(
        set(filter(lambda s: len(s) > 0, map(str.strip, text.split(delimiter))))
    )


def build_url(base_url: str, params: Dict[str, Any]) -> str:
    return base_url + "?" + urlencode(params)


def next_page_url(browse_data: BrowseData, url: str, shorts: bool) -> str | None:
    if browse_data.continuation_token is not None:
        return build_url(
            url,
            {
                "click_tracking_params": browse_data.click_tracking_params,
                "continuation_token": browse_data.continuation_token,
                "shorts": shorts,
            },
        )
