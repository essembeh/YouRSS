"""
webapp api
"""

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restful import Api, Resource

from .channel import ChannelApi, FetchApi
from .jwt import Token
from .test import Test, TestAuth
from .user import ConfigApi, SubscriptionApi


def create_api(prefix: str = None):
    out = Api(prefix=prefix)
    out.add_resource(Token, "/auth")

    out.add_resource(ConfigApi, "/config")
    out.add_resource(
        SubscriptionApi, "/subscription", "/subscription/<string:channel_id>"
    )
    out.add_resource(ChannelApi, "/channel", "/channel/<string:channel_id>")
    out.add_resource(FetchApi, "/channel/<string:channel_id>/fetch")

    out.add_resource(Test, "/test")
    out.add_resource(TestAuth, "/testauth")
    return out


api = create_api(prefix="/api")
jwt = JWTManager()
