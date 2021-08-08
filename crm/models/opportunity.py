from crm.models.resource import BaseResource
from crm.models.account import Account
from crm.fields import TextField, ReferenceField


class Opportunity(BaseResource):
    name = TextField()
    description = TextField()

    account = ReferenceField(Account)
