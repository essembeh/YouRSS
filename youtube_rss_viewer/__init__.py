"""
project metadata
"""

import json
from re import split

from flask import Flask, current_app, jsonify, render_template, request
from flask.helpers import url_for
from werkzeug.utils import redirect

from .youtube import get_channel_feed, get_user_feed

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

__version__ = importlib_metadata.version(__name__)


def create_app():
    app = Flask(__name__)
    app.config["TEMPLATES_AUTO_RELOAD"] = True

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
        if len(request.args) > 0:
            return redirect(url_for("view", **request.args))
        return redirect(url_for("view", q="UCa_Dlwrwv3ktrhCy91HpVRw,Jonnyswitzerland"))

    @app.route("/view", methods=["GET"])
    def view():

        channels = {}
        query = request.args.get("q").split(",")
        if query is not None:
            for channel_id in request.args.get("q").split(","):
                channel = (
                    get_channel_feed(channel_id)
                    if len(channel_id) == 24
                    else get_user_feed(channel_id)
                )
                if channel:
                    channels[channel.channel_id] = channel
        return render_template(
            "grid.html",
            channels=channels,
            sorted_videos=sorted(
                (v for channel in channels.values() for v in channel.entries),
                reverse=True,
            ),
        )

    @app.route("/list", methods=["GET"])
    def view_list():

        channels = {}
        query = request.args.get("q").split(",")
        if query is not None:
            for channel_id in request.args.get("q").split(","):
                channel = (
                    get_channel_feed(channel_id)
                    if len(channel_id) == 24
                    else get_user_feed(channel_id)
                )
                if channel:
                    channels[channel.channel_id] = channel
        return render_template(
            "list.html",
            channels=channels,
            sorted_videos=sorted(
                (v for channel in channels.values() for v in channel.entries),
                reverse=True,
            ),
        )

    return app
