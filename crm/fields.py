import json
from enum import Enum
from werkzeug.security import check_password_hash, generate_password_hash

from crm.db import db
from crm.access import AccessControlList


class FieldValueCache:
    def __init__(self, resource, field):
        self.value = None

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value


class Field:
    def __init__(self, column_type, *args, label=None, widget=None, cache=FieldValueCache, acl=None, **kwargs):
        self.name = None
        self.resource = None
        self.cache = cache
        self.label = label
        self.widget = widget
        self.column_type = column_type
        self.acl = acl or AccessControlList()
        self.column_args = args
        self.column_kwargs = kwargs

    def create_column(self):
        if self.column_type is None:
            return None

        return db.Column(self.column_type, *self.column_args, **self.column_kwargs)

    @property
    def column(self):
        return getattr(self.resource.model, self.name)

    def check_access(self, resource, user, access_type):
        return self.acl.check(resource, user, access_type)

    def retrieve(self, resource):
        return getattr(resource.instance, self.name)

    def persist(self, resource, cache):
        value = self.to_storage(cache.get_value())
        setattr(resource.instance, self.name, value)

    def to_storage(self, value):
        return value

    def from_storage(self, value):
        return value

    def compare(self, stored, value):
        return stored == value

    def set_value(self, resource, value):
        resource._set_field(self, value)

    def merge_cache(self, cache, value):
        cached_value = cache.get_value()

        if cached_value is not None:
            return cached_value

        return value

    def get_persisted_value(self, resource):
        return self.from_storage(self.retrieve(resource))

    def get_value(self, resource, cache):
        cached = cache.get_value()

        if cached is not None:
            return cached

        return self.get_persisted_value(resource)

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

    def set_value(self, instance, password, confirmation=None):
        if password == '':
            return

        if confirmation is not None and password != confirmation:
            raise ValueError(f'Confirmation for field {self.label} does not match.')

        return super().set_value(instance, password)

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

    def set_value(self, instance, value):
        if value.filename == '':
            return

        from crm.models import File
        print('create_from', type(value), value)
        file = File.create_from(value.stream, name=value.filename)
        super().set_value(instance, file)


class ReferenceField(Field):
    def __init__(self, resource_type=None, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = 'reference'

        self.resource_type = resource_type

        super().__init__(db.Integer, db.ForeignKey('resource.id'), *args, **kwargs)

    def from_storage(self, resource_id):
        from crm.models import Resource
        return Resource.get_resource(resource_id)

    def to_storage(self, instance):
        return instance.id

    def set_value(self, instance, value):
        from crm.models import Resource

        if isinstance(value, str):
            value = Resource.get_resource(int(value))

        super().set_value(instance, value)

    def get_options(self):
        return json.dumps([
            { "id": instance.id, "type": self.resource_type.__name__, "title": instance.title() }
            for instance in self.resource_type.all()
        ])


class TableFieldCache:
    def __init__(self, resource, field):
        self.field = field
        self.resource = resource
        self.mutations = []

    def get_value(self):
        return None

        fmodel = self.field.foreign_type.model
        fcolumn = self.field.foreign_field.column
        local_id = self.resource.id

        return fmodel.query.filter(fcolumn == local_id).all()

    def remove_row(self, row):
        self.mutations.append(('remove', row))

    def add_row(self, row):
        self.mutations.append(('add', row))


class TableField(Field):
    def __init__(self, foreign_field, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = 'table'

        self._foreign_field_ref = foreign_field
        self._foreign_field = None

        super().__init__(None, cache=TableFieldCache, *args, **kwargs)

    @property
    def foreign_field(self):
        if self._foreign_field is not None:
            return self._foreign_field

        if isinstance(self._foreign_field_ref, str):
            self._foreign_field = self.resource.resolve_resource(self._foreign_field_ref)
        else:
            self._foreign_field = self._foreign_field_ref

        return self._foreign_field

    @property
    def foreign_type(self):
        return self.foreign_field.resource

    def persist(self, resource, cache):
        pass

    def retrieve(self, resource):
        if resource.id is None:
            return []

        return [
            self.foreign_field.resource(from_instance=i)
            for i in self.foreign_type.model.query.filter(self.foreign_field.column == resource.id).all()
        ]

    def set_value(self, resource, value):
        pass

    @staticmethod
    def get_value_json(bound):
        return json.dumps([
            { "id": row.id, "title": row.title() }
            for row in bound.get()
        ])
