from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with, inputs
from flask_restful.reqparse import RequestParser

from ..database import User, db, Channel, Subscription
from .channel import find_or_create_channel
from ..utils import validate_email, validate_password
from ..youtube import youtube_find_channel_infos

CONFIG_FIELDS = {
    "name": fields.String,
    "email": fields.String,
    "avatar": fields.String,
    "labels": fields.List(
        fields.String,
        attribute=lambda u: sorted(
            set(s.label for s in u.subscriptions if s.label is not None and s.enabled)
        ),
    ),
}
SUBSCRIPTION_FIELDS = {
    "channel_id": fields.String,
    "label": fields.String,
    "enabled": fields.Boolean,
    "name": fields.String(attribute="channel.name"),
    "avatar": fields.String(attribute="channel.avatar"),
}


class ConfigApi(Resource):
    @jwt_required()
    @marshal_with(CONFIG_FIELDS)
    def get(self):
        return User.find_by_email(get_jwt_identity()) or abort(404)

    @jwt_required()
    @marshal_with(CONFIG_FIELDS)
    def put(self):
        user = User.find_by_email(get_jwt_identity()) or abort(404)

        parser = RequestParser()
        parser.add_argument("name", location="json")
        parser.add_argument("email", type=validate_email, location="json")
        parser.add_argument("avatar", location="json")
        parser.add_argument("password", type=validate_password, location="json")
        parser.add_argument("old_password", location="json")
        args = parser.parse_args()
        print(">>>", args)
        if args.name:
            user.name = args.name
        if args.email:
            user.email = args.email
        if args.avatar is not None:
            # TODO check mimetype
            user.avatar = args.avatar
        if args.password:
            if args.old_password and not user.check_password(args.old_password):
                abort(500, "Invalid current password")
            user.set_password(args.password)

        db.session.commit()
        return user


def find_or_create_channel(youtube_id: str):
    channel = Channel.query.get(youtube_id)
    if channel is None:
        channel_info = youtube_find_channel_infos(youtube_id)
        channel = Channel(**channel_info)
        db.session.add(channel)
        db.session.commit()
    return channel


class SubscriptionApi(Resource):
    @jwt_required()
    @marshal_with(SUBSCRIPTION_FIELDS)
    def get(self, channel_id: str = None):
        user = User.find_by_email(get_jwt_identity()) or abort(404)
        return user.subscriptions

    @jwt_required()
    @marshal_with(SUBSCRIPTION_FIELDS)
    def post(self):
        user = User.find_by_email(get_jwt_identity()) or abort(404)

        parser = RequestParser()
        parser.add_argument("channel_id", location="json")
        parser.add_argument("url", location="json")
        parser.add_argument("label", location="json")
        parser.add_argument("enabled", type=inputs.boolean, location="json")
        args = parser.parse_args()

        channel = None
        if args.channel_id:
            # get or create by id
            channel = Channel.query.get(args.channel_id)
            if not channel:
                channel_infos = youtube_find_channel_infos(args.channel_id)
                channel = Channel(**channel_infos)
                db.session.add(channel)

        if not channel and args.url:
            # get infos
            channel_infos = youtube_find_channel_infos(args.url)
            channel = Channel.query.get(channel_infos["id"])
            if not channel:
                channel_infos = youtube_find_channel_infos(channel_infos["id"])
                channel = Channel(**channel_infos)
                db.session.add(channel)

        if not channel:
            abort(500, "Cannot retrieve channel informations")

        assert channel
        sub = next(filter(lambda s: s.channel == channel, user.subscriptions), None)
        if sub:
            abort(500, f"Already subscribed to {sub.channel_id}")

        sub = Subscription(
            channel=channel, user=user, label=args.label, enabled=args.enabled
        )
        db.session.add(sub)

        db.session.commit()
        return sub

    @jwt_required()
    @marshal_with(SUBSCRIPTION_FIELDS)
    def put(self, channel_id: str):
        user = User.find_by_email(get_jwt_identity()) or abort(404)

        parser = RequestParser()
        parser.add_argument("label", location="json")
        parser.add_argument("enabled", type=inputs.boolean, location="json")
        args = parser.parse_args()

        sub = next(
            filter(lambda s: s.channel_id == channel_id, user.subscriptions), None
        )
        if sub is None:
            abort(500, f"Not subscribed to {channel_id}")

        sub.enabled = args.enabled
        sub.label = args.label or None
        db.session.commit()
        return sub

    @jwt_required()
    def delete(self, channel_id: str):
        user = User.find_by_email(get_jwt_identity()) or abort(404)
        if not user.unsubscribe(channel_id):
            abort(500, "cannot find subscription")
        db.session.commit()
        return "ok"
