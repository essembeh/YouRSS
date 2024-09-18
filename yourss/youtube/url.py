import re

from loguru import logger

from .metadata import CHANNEL_PATTERN


class YoutubeUrl:
    @staticmethod
    def thumbnail(video_id: str, instance: int = 1) -> str:
        return f"https://i{instance}.ytimg.com/vi/{video_id}/hqdefault.jpg"

    @staticmethod
    def channel_rss(channel_id: str) -> str:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    @staticmethod
    def user_rss(user: str) -> str:
        return f"https://www.youtube.com/feeds/videos.xml?user={user}"

    @staticmethod
    def playlist_rss(playlist: str) -> str:
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist}"

    @classmethod
    def slug_home(cls, slug: str) -> str:
        assert slug.startswith("@")
        return f"https://www.youtube.com/{slug}"

    @classmethod
    def channel_home(cls, channel_id: str) -> str:
        assert re.fullmatch(CHANNEL_PATTERN, channel_id)
        return f"https://www.youtube.com/channel/{channel_id}"

    @classmethod
    def user_home(cls, user: str) -> str:
        return f"https://www.youtube.com/user/{user}"

    @classmethod
    def home(cls, anything: str) -> str:
        if anything.startswith("@"):
            logger.debug("Guess {} looks like a slug", anything)
            return cls.slug_home(anything)
        elif re.fullmatch(CHANNEL_PATTERN, anything):
            logger.debug("Guess {} looks like a channel", anything)
            return cls.channel_home(anything)
        else:
            logger.debug("Guess {} looks like a user", anything)
            return cls.user_home(anything)
