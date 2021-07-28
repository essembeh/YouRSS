"""
authentication api
"""
from datetime import timedelta

from flask import jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_login import current_user
from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from ..database import User


class Token(Resource):
    def post(self):

        parser = RequestParser()
        parser.add_argument("login", location=["json"], required=True)
        parser.add_argument("password", location=["json"], required=True)
        args = parser.parse_args()
        user = User.find_by_email(args.login)
        if user and user.check_password(args.password):
            access_token = create_access_token(
                identity=user.email, expires_delta=timedelta(days=1)
            )
            return jsonify(access_token=access_token)
        return jsonify({"msg": "Bad login or password"}), 401

    def get(self):
        if current_user and current_user.is_authenticated:
            access_token = create_access_token(
                identity=current_user.user.email, expires_delta=timedelta(days=1)
            )
            out = jsonify(access_token=access_token)
            set_access_cookies(out, access_token)
            return out
        return jsonify({"msg": "Bad login or password"}), 401
