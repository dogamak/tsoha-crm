from crm.db import db
from crm.models.resource import Section
from crm.access import AccessControlList, AccessControlGroup

from enum import Enum

from .resource import BaseResource, FileField, TextField, PasswordField, ChoiceField

from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(Enum):
    Administrator = 'Administrator'
    Sales = 'Sales'

class User(BaseResource):
    __acl__ = AccessControlList('r=o,w=sAO,d=AO,c=A')

    username = TextField(unique=True)
    password = PasswordField(acl=AccessControlList('w=As'))
    role = ChoiceField(UserRole, acl=AccessControlList('w=A'))
    avatar = FileField()

    assigned_resources = db.relationship('Resource', secondary='resource_user')

    def title(self):
        return self.username
