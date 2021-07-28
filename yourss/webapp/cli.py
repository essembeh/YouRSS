"""
flask commands for webapp administration
"""

import click
from flask.cli import with_appcontext

from ..database import db, User


@click.command("init-db")
@with_appcontext
def init_db_command():
    db.create_all()


@click.command("add-user")
@click.argument("name")
@click.argument("email")
@click.argument("password")
@with_appcontext
def add_user_command(name: str, email: str, password: str):
    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()


@click.command("check-user")
@click.argument("email")
@click.argument("password")
@with_appcontext
def check_user_command(email: str, password: str):
    user = User.find_by_email(email)
    if user is None:
        click.echo(f"Cannot find user {email}")
    elif user.check_password(password):
        click.echo(f"Password for user {user.email} is valid: {user.password}")
    else:
        click.echo(f"Password for user {user.email} is not valid")


@click.command("remove-user")
@click.argument("email")
@with_appcontext
def remove_user_command(email: str):
    user = User.find_by_email(email)
    if user is None:
        click.echo(f"Cannot find user {email}")
    else:
        db.session.delete(user)
        db.session.commit()
        click.echo(f"User {user.email} was removed")


@click.command("list-users")
@with_appcontext
def list_users_command():
    for user in User.query.all():
        click.echo(f"{user.email} ({user.name}): {user.password}")
