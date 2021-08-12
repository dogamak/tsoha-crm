from .user import User
from .account import Account
from .file import File
from .opportunity import Opportunity
from .sales_order import SalesOrder
from .resource_log import ResourceLog
from .resource import BaseResource

Resource = BaseResource.create_resource_table()
