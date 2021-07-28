from pathlib import Path
from yourss.webapp import app, db
from yourss.database import User, Channel, Subscription
from yourss.api.channel import find_or_create_channel


def test_create():

    dbfile = Path("/tmp/yourss.sqlite")
    if dbfile.exists():
        dbfile.unlink()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{dbfile}"

    with app.app_context():
        db.create_all()
        assert User.query.count() == 0
        assert Subscription.query.count() == 0
        assert Channel.query.count() == 0

        user = User(email="test@pytest", name="test")
        db.session.add(user)
        assert User.query.count() == 1
        assert Subscription.query.count() == 0
        assert Channel.query.count() == 0

        channel = find_or_create_channel("UCa_Dlwrwv3ktrhCy91HpVRw")
        db.session.add(channel)
        assert User.query.count() == 1
        assert Subscription.query.count() == 0
        assert Channel.query.count() == 1


def test_subscribe():
    dbfile = Path("/tmp/yourss.sqlite")
    if dbfile.exists():
        dbfile.unlink()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{dbfile}"

    with app.app_context():
        db.create_all()

        user = User(email="test@pytest", name="test")
        db.session.add(user)
        channel = find_or_create_channel("UCa_Dlwrwv3ktrhCy91HpVRw")
        db.session.add(channel)

        user.subscribe(channel)
        assert User.query.count() == 1
        assert Subscription.query.count() == 1
        assert Channel.query.count() == 1

        user.unsubscribe(channel)
        assert User.query.count() == 1
        assert Subscription.query.count() == 0
        assert Channel.query.count() == 1


def test_delete_user():
    dbfile = Path("/tmp/yourss.sqlite")
    if dbfile.exists():
        dbfile.unlink()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{dbfile}"

    with app.app_context():
        db.create_all()

        user = User(email="test@pytest", name="test")
        db.session.add(user)
        channel = find_or_create_channel("UCa_Dlwrwv3ktrhCy91HpVRw")
        db.session.add(channel)
        user.subscribe(channel)
        assert User.query.count() == 1
        assert Subscription.query.count() == 1
        assert Channel.query.count() == 1

        db.session.delete(user)
        assert User.query.count() == 0
        assert Subscription.query.count() == 0
        assert Channel.query.count() == 1


def test_delete_channel():
    dbfile = Path("/tmp/yourss.sqlite")
    if dbfile.exists():
        dbfile.unlink()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{dbfile}"

    with app.app_context():
        db.create_all()

        user = User(email="test@pytest", name="test")
        db.session.add(user)
        channel = find_or_create_channel("UCa_Dlwrwv3ktrhCy91HpVRw")
        db.session.add(channel)
        user.subscribe(channel)
        assert User.query.count() == 1
        assert Subscription.query.count() == 1
        assert Channel.query.count() == 1

        db.session.delete(channel)
        assert User.query.count() == 1
        assert Subscription.query.count() == 0
        assert Channel.query.count() == 0


def test_delete_subscription():
    dbfile = Path("/tmp/yourss.sqlite")
    if dbfile.exists():
        dbfile.unlink()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{dbfile}"

    with app.app_context():
        db.create_all()

        user = User(email="test@pytest", name="test")
        db.session.add(user)
        channel = find_or_create_channel("UCa_Dlwrwv3ktrhCy91HpVRw")
        db.session.add(channel)
        sub = user.subscribe(channel)
        assert User.query.count() == 1
        assert Subscription.query.count() == 1
        assert Channel.query.count() == 1

        db.session.delete(sub)
        assert User.query.count() == 1
        assert Subscription.query.count() == 0
        assert Channel.query.count() == 1
