from crm.db import db
from enum import Enum

from .resource import BaseResource, TextField, PasswordField, ChoiceField

from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(Enum):
    Administrator = 'Administrator'
    Sales = 'Sales'

class User(BaseResource):
    username = TextField(unique=True)
    password = PasswordField()
    role = ChoiceField(UserRole)

    assigned_resources = db.relationship('Resource', secondary='resource_user')

    def title(self):
        return self.username


