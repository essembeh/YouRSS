from .rss import RssFeed


def get_channel_feed(channel_id: str):
    """
    from a channel id, retrieve rss feed and parse available videos
    """
    return RssFeed.fromurl(
        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    )


def get_user_feed(user: str):
    """
    from a user, retrieve rss feed and parse available videos
    """
    return RssFeed.fromurl(f"https://www.youtube.com/feeds/videos.xml?user={user}")
