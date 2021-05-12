"""
project metadata
"""

import json
from re import split

from flask import Flask, jsonify, request, current_app
from flask.helpers import url_for
from werkzeug.utils import redirect

from .youtube import get_channel_feed, get_user_feed

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

__version__ = importlib_metadata.version(__name__)


def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/",
    )

    @app.route("/fetch/<string:channels>")
    def fetch(channels):
        videos = {}
        for channel in channels.split(","):
            feed = (
                get_channel_feed(channel)
                if len(channel) == 24
                else get_user_feed(channel)
            )
            if feed:
                for video in feed.entries:
                    videos[video] = feed
        out = sorted(videos.keys(), key=lambda v: v.updated_date, reverse=True)
        return jsonify(
            [
                {
                    "channel_id": videos[v].channel_id,
                    "channel_name": videos[v].title,
                    "video_id": v.video_id,
                    "video_title": v.title,
                    "video_link": v.link,
                    "video_published": v.published,
                    "video_updated": v.updated,
                    "video_thumbnail": v.thumbnail_url,
                    "video_description": v.description,
                }
                for v in out
            ]
        )

    @app.route("/", methods=["GET"])
    def redirect_to_index():
        return current_app.send_static_file("index.html")

    return app
