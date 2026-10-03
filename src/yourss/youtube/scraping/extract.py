"""Pull the JSON documents embedded in a Youtube HTML page, without parsing the HTML."""

import json
import re
from typing import Any

from .errors import ScrapingError

# Youtube embeds its data as `var ytInitialData = {…};`, `window["ytInitialData"] = {…};`
# or `<script id="yt-initial-data" type="application/json">{…}</script>`
INITIAL_DATA_PATTERN = re.compile(
    r"""(?:ytInitialData(?:["']\])?\s*=\s*|<script\b[^>]*\bid="yt-initial-data"[^>]*>\s*)(?={)"""
)
CLIENT_VERSION_PATTERN = re.compile(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"')

_decoder = json.JSONDecoder()


def extract_json(html: str, pattern: re.Pattern[str]) -> dict[str, Any] | None:
    """Decode the JSON object which follows ``pattern``; ``None`` when absent or invalid."""
    for match in pattern.finditer(html):
        try:
            out, _ = _decoder.raw_decode(html, match.end())
        except ValueError:
            continue
        if isinstance(out, dict):
            return out
    return None


def extract_initial_data(html: str) -> dict[str, Any]:
    """The ``ytInitialData`` document: everything the page displays."""
    out = extract_json(html, INITIAL_DATA_PATTERN)
    if out is None:
        # Quote what the page holds instead: this is what a fix will be written from
        position = html.find("ytInitialData")
        context = (
            html[max(0, position - 20) : position + 80]
            if position >= 0
            else "no occurrence"
        )
        raise ScrapingError(
            f"Cannot read ytInitialData in a Youtube page of {len(html)} chars: {context!r}"
        )
    return out


def extract_client_version(html: str) -> str | None:
    """Version of the Youtube web client, required to ask for the next page of a tab."""
    match = CLIENT_VERSION_PATTERN.search(html)
    return match.group(1) if match else None
