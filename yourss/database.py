"""
represent a user in database
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

LABEL_PATTERN = r"[a-zA-Z0-9 _-]+"


class User(db.Model):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    email = Column(String(256), unique=True, nullable=False)
    password = Column(String(256))
    avatar = Column(String(256))
    enabled = Column(Boolean, default=True)

    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="delete, delete-orphan",
    )

    @classmethod
    def find_by_email(cls, email: str):
        return cls.query.filter(cls.email == email).filter(cls.enabled).first()

    def check_password(self, password: str):
        return check_password_hash(self.password, password)

    def set_password(self, password: str):
        self.password = generate_password_hash(password)

    def subscribe(self, channel, enabled: bool = None, label: str = None):
        # find if exists
        sub = next(filter(lambda s: s.channel == channel, self.subscriptions), None)
        # create if needed
        if sub is None:
            sub = Subscription(channel=channel)
            db.session.add(sub)
            self.subscriptions.append(sub)
        # update attributes
        if enabled is not None:
            sub.enabled = enabled
        if label is not None:
            sub.label = label
        return sub

    def unsubscribe(self, channel_id):
        sub = next(
            filter(lambda s: s.channel_id == channel_id, self.subscriptions), None
        )
        if sub:
            self.subscriptions.remove(sub)
            return True
        return False


class Subscription(db.Model):
    __tablename__ = "subscription"

    user_id = Column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    channel_id = Column(ForeignKey("channel.id", ondelete="CASCADE"), primary_key=True)
    label = Column(String(64))
    enabled = Column(Boolean, default=True)

    user = relationship(
        "User",
        back_populates="subscriptions",
    )
    channel = relationship(
        "Channel",
        back_populates="subscribers",
    )


class Channel(db.Model):
    __tablename__ = "channel"

    id = Column(String(64), primary_key=True)
    name = Column(String(64))
    avatar = Column(String(256))
    rss_url = Column(String(256))

    subscribers = relationship(
        "Subscription",
        back_populates="channel",
        cascade="delete, delete-orphan",
    )
