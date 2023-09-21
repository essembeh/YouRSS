from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from .model import RssFeed
from .youtube import youtube_get_rss_feed


def parallel_fetch(names: Iterable[str], workers: int = 4) -> dict[str, RssFeed | None]:
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        jobs = {executor.submit(youtube_get_rss_feed, x): x for x in set(names)}
        for job in as_completed(jobs):
            name = jobs[job]
            try:
                out[name] = RssFeed.fromresponse(job.result())
            except BaseException:
                out[name] = None
    return out


def parse_channel_names(
    text: str, delimiter: str = ",", disabled_prefix: str = "-"
) -> dict[str, bool]:
    return {
        s.removeprefix(disabled_prefix): not s.startswith(disabled_prefix)
        for s in filter(
            lambda x: len(x.removeprefix(disabled_prefix)) > 0, text.split(delimiter)
        )
    }
