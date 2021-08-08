from crm.models.resource import BaseResource, Section
from crm.fields import TextField, TableField


class Account(BaseResource):
    name = TextField()
    description = TextField()
    email = TextField(label='E-Mail Address')
    phone = TextField(label='Phone Number')
    mail_address = TextField(label='Mail Address')
    billing_address = TextField(label='Billing Address')
    opportunities = TableField('Opportunity.account')

    __layout__ = [
        Section(None, [ name, description, email, phone, mail_address, billing_address ]),
        Section(None, [ opportunities ]),
    ]

    def title(self):
        return self.name
