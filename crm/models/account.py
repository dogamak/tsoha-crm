from .resource import BaseResource, TextField


class Account(BaseResource):
    name = TextField()
    description = TextField()
    email = TextField(label='E-Mail Address')
    phone = TextField(label='Phone Number')
    mail_address = TextField(label='Mail Address')
    billing_address = TextField(label='Billing Address')

    def title(self):
        return self.name
