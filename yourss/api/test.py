"""
webapp api
"""
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource


class Test(Resource):
    def get(self):
        return {"hello": "world"}


class TestAuth(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        return {"hello": current_user}
