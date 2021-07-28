from flask_jwt_extended import jwt_required
from flask_restful import Resource, fields, marshal_with

from ..database import Channel, db
from ..rss import RssFeed
from ..youtube import youtube_find_channel_infos


FEED_VIDEO_FIELDS = {
    "video_id": fields.String,
    "title": fields.String,
    "link": fields.String,
    "published": fields.String,
    "updated": fields.String,
    "thumbnail_url": fields.String,
    "description": fields.String,
}
FEED_FIELDS = {
    "channel_id": fields.String,
    "name": fields.String,
    "link": fields.String,
    "videos": fields.List(fields.Nested(FEED_VIDEO_FIELDS), attribute="entries"),
}
CHANNEL_FIELDS = {
    "id": fields.String,
    "name": fields.String,
    "avatar": fields.String,
    "rss_url": fields.String,
}


def find_or_create_channel(youtube_id: str):
    channel = Channel.query.get(youtube_id)
    if channel is None:
        channel_info = youtube_find_channel_infos(youtube_id)
        channel = Channel(**channel_info)
        db.session.add(channel)
        db.session.commit()
    return channel


class FetchApi(Resource):
    @jwt_required()
    @marshal_with(FEED_FIELDS)
    def get(self, channel_id: str):
        channel = find_or_create_channel(channel_id)
        rssfeed = RssFeed.fromurl(channel.rss_url)
        return rssfeed


class ChannelApi(Resource):
    @jwt_required()
    @marshal_with(CHANNEL_FIELDS)
    def get(self, channel_id: str):
        return find_or_create_channel(channel_id)
