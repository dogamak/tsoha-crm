from crm.models.resource import BaseResource
from crm.models.account import Account
from crm.fields import TextField, TableField, ReferenceField


class Opportunity(BaseResource):
    name = TextField()
    description = TextField()

    account = ReferenceField(Account)
    sales_orders = TableField('SalesOrder.opportunity')
