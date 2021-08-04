from enum import Enum
from werkzeug.security import check_password_hash, generate_password_hash

from crm.db import db
from crm.access import AccessControlList

class Field:
    def __init__(self, column_type, *args, label=None, widget=None, acl=None, **kwargs):
        self.name = None
        self.resource = None
        self.label = label
        self.widget = widget
        self.column_type = column_type
        self.column = db.Column(column_type, *args, **kwargs)
        self.acl = acl or AccessControlList()

    def check_access(self, resource, user, access_type):
        return self.acl.check(resource, user, access_type)

    def to_storage(self, value):
        return value

    def from_storage(self, value):
        return value

    def compare(self, stored, value):
        return stored == value

    def on_set(self, instance, value):
        storage_value = self.to_storage(value)
        instance._set_field(self.name, storage_value)

    def _assign(self, name, resource):
        self.name = name
        self.resource = resource

        if self.label is None:
            self.label = name[0].upper() + name[1:] 


class TextField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = 'text'

        super().__init__(db.String, *args, widget=widget, **kwargs)

    def from_storage(self, value):
        if value is None:
            return ''

        return value


class PasswordField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = 'password'

        super().__init__(db.String, *args, widget=widget, **kwargs)

    def to_storage(self, password):
        return generate_password_hash(password)

    def from_storage(self, hash):
        return '*******'

    def on_set(self, instance, password, confirmation=None):
        if password == '':
            return

        if confirmation is not None and password != confirmation:
            raise ValueError(f'Confirmation for field {self.label} does not match.')

        return super().on_set(instance, password)

    def compare(self, hash, password):
        return check_password_hash(hash, password)


class ChoiceField(Field):
    def __init__(self, variants, *args, **kwargs):
        self.variants = variants

        if 'widget' not in kwargs:
            kwargs['widget'] = 'choice'
        
        super().__init__(db.String, *args, **kwargs)

    def to_storage(self, value):
        if issubclass(self.variants, Enum):
            if isinstance(value, Enum):
                return value.value
            elif isinstance(value, str):
                self.variants(value)
                return value
        elif isinstance(value, str) and isinstance(self.variants, list):
            if value in self.variants:
                return value
            else:
                raise ValueError(f'Invalid variant "{value}"')

        raise ValueError(f'Unknown variant "{value}"')


    def from_storage(self, value):
        if value is None:
            return None

        if issubclass(self.variants, Enum):
            return self.variants(value)

        return value


class FileField(Field):
    def __init__(self, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = 'image'
        
        super().__init__(db.String, db.ForeignKey('file.hash'), *args, **kwargs)

    def from_storage(self, hash):
        from crm.models import File
        return File.query.get(hash)

    def to_storage(self, value):
        print('to_storage', value)
        db.session.add(value)
        return value.hash

    def on_set(self, instance, value):
        if value.filename == '':
            return

        from crm.models import File
        print('create_from', type(value), value)
        file = File.create_from(value.stream, name=value.filename)
        super().on_set(instance, file)
