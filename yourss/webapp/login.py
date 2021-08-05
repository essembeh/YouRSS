"""
login management
"""
from flask_login import LoginManager, login_user, logout_user
from ..database import User
from dataclasses import dataclass

login_manager = LoginManager()
login_manager.login_view = "route_login"


@dataclass
class WebUser:

    user: User

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.user.id

    @classmethod
    def find(cls, login: str):
        user = User.query.filter(User.email == login).first()
        return cls(user) if user else None


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    return WebUser(user) if user else None
