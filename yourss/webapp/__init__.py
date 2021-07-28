"""
"""
from os import environ

from .. import __name__ as appname
from ..api import api, jwt
from ..database import db
from .login import login_manager
from .server import initialize_app

app = initialize_app(appname, environ["APP_SECRETKEY"], environ["APP_DATABASE"])
db.init_app(app)
jwt.init_app(app)
api.init_app(app)
login_manager.init_app(app)
