from crm.models.resource import BaseResource, Section
from crm.models.opportunity import Opportunity
from crm.fields import TextField, ReferenceField, DateField, CurrencyField


class SalesOrder(BaseResource):
    opportunity = ReferenceField(Opportunity)
    description = TextField()
    start_date = DateField()
    end_date = DateField()
    base_price = CurrencyField()
    hourly_price = CurrencyField()

    __layout__ = [
        Section(None, [ opportunity, description ]),
        Section(None, [ start_date, end_date ]),
        Section(None, [ base_price, hourly_price ]),
    ]
