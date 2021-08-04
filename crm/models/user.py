from enum import Enum

from crm.access import AccessControlList, AccessControlGroup
from crm.db import db
from crm.fields import FileField, TextField, PasswordField, ChoiceField
from crm.models.resource import Section, BaseResource

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
