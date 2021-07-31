from crm.db import db
from enum import Enum

from .resource import BaseResource, TextField, PasswordField, ChoiceField

from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(Enum):
    Administrator = 'Administrator'
    Sales = 'Sales'

class User(BaseResource):
    # id = db.Column(db.Integer, primary_key=True)
    # username = db.Column(db.String, unique=True, nullable=False)
    # role = db.Column(db.Enum(UserRole), nullable=False)
    # password_hash = db.Column(db.String)
    username = TextField(unique=True)
    password = PasswordField()
    role = ChoiceField(UserRole)

    def title(self):
        return self.username


