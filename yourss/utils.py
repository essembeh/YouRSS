from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from .model import RssFeed
from .youtube import youtube_fetch_rss_feed


def parallel_fetch(names: Iterable[str], workers: int = 4) -> list[RssFeed]:
    out = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for job in as_completed(
            map(lambda x: executor.submit(youtube_fetch_rss_feed, x), names)
        ):
            try:
                out.append(RssFeed.fromresponse(job.result()))
            except BaseException:
                pass
    return out
