"""
server implementation
"""

from datetime import timedelta

from flask import Flask, render_template, request
from flask.helpers import url_for
from flask_jwt_extended import unset_jwt_cookies
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import redirect

from .cli import (
    add_user_command,
    check_user_command,
    init_db_command,
    list_users_command,
    remove_user_command,
)
from .login import WebUser


def initialize_app(name: str, secretkey: str, db_uri=str, **kwargs):
    # create the server
    app = Flask(name, static_folder="static", static_url_path="/", **kwargs)

    app.config.from_mapping(
        # flask
        SECRET_KEY=secretkey,
        TEMPLATES_AUTO_RELOAD=True,
        # orm
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_RECORD_QUERIES=True,
        # jwt
        JWT_SECRET_KEY=secretkey,
        JWT_TOKEN_LOCATION=["headers", "cookies"],
        JWT_COOKIE_SECURE=True,
        JWT_COOKIE_CSRF_PROTECT=False,
        JWT_CSRF_IN_COOKIES=True,
    )

    # flask command line interface
    app.cli.add_command(init_db_command)
    app.cli.add_command(add_user_command)
    app.cli.add_command(list_users_command)
    app.cli.add_command(check_user_command)
    app.cli.add_command(remove_user_command)

    @app.route("/", methods=["GET"])
    def route_index():
        if current_user and current_user.is_authenticated:
            return redirect(url_for("route_view"))
        return redirect(url_for("route_login"))

    # login page
    @app.route("/login", methods=["GET", "POST"])
    def route_login():
        if request.method == "POST":
            login, password = request.form["login"], request.form["password"]
            user = WebUser.find(login)
            if user and user.user.check_password(password):
                login_user(user)
                return redirect(url_for("route_view", **request.args))
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def route_logout():
        logout_user()
        out = redirect(url_for("route_index"))
        unset_jwt_cookies(out)
        return out

    @app.route("/view", methods=["GET"])
    @login_required
    def route_view():
        return render_template("view.html", user=current_user.user)

    @app.route("/subscriptions", methods=["GET"])
    @login_required
    def route_channels():
        return render_template("subscriptions.html", user=current_user.user)

    return app
