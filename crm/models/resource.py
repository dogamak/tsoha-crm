from crm.db import db

import inspect
from sqlalchemy import event
from flask_sqlalchemy.model import DefaultMeta

from enum import Enum
from werkzeug.security import check_password_hash, generate_password_hash

class Field:
    def __init__(self, column_type, *args, label=None, widget=None, **kwargs):
        self.name = None
        self.resource = None
        self.label = label
        self.widget = widget
        self.column_type = column_type
        self.column = db.Column(column_type, *args, **kwargs)

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
        if issubclass(self.variants, Enum):
            return self.variants(value)
        else:
            return value


def isfield(value):
    print(value)
    return isinstance(value, Field)


resource_classes = []


def create_resource_table():
    properties = dict(
        id = db.Column(db.Integer, primary_key=True),
    )

    for cls in resource_classes:
        column_name = cls.model.__tablename__ + '_id'
        properties[column_name] = db.Column(db.Integer, db.ForeignKey(getattr(cls.model, 'variant_id')))
        properties[cls.model.__tablename__] = db.relationship(cls.model, back_populates='_resource')

    cls = DefaultMeta('Resource', (db.Model,), properties)

    def get_resource(id):
        resource = cls.query.get(id)

        if resource is None:
            return None

        for c in resource_classes:
            column_name = c.model.__tablename__ + '_id'
            id = getattr(resource, column_name)

            if id is not None:
                return c.get(id)

        raise Exception('invalid resource')

    def from_instance(obj):
        for c in resource_classes:
            if not isinstance(obj, c):
                continue

            columns = dict()
            columns[c.model.__tablename__] = obj.instance

            return cls(**columns)

        raise ValueError('not an instance of a known resource class')
        

    setattr(cls, 'get_resource', get_resource)
    setattr(cls, 'from_instance', from_instance)

    return cls


class ResourceMeta(type):
    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)

    def __new__(cls, clsname, bases, d):
        fields = dict()

        inst = super(ResourceMeta, cls).__new__(cls, clsname, bases, d)

        if d.get('__abstract__', False):
            return inst

        model_dict = dict(
            variant_id = db.Column('id', db.Integer, primary_key=True),
            _resource = db.relationship('Resource', uselist=False),
        )

        for name, value in vars(inst).items():
            if not isinstance(value, Field):
                continue

            model_dict[name] = value.column
            value._assign(name, inst)
            fields[name] = value

        for field in fields.values():
            delattr(inst, field.name)

        resource_classes.append(inst)

        model = DefaultMeta(clsname, (db.Model,), model_dict)

        setattr(inst, 'model', model)
        setattr(inst, '_fields', fields)
        print(inst)

        return inst


class BoundField:
    def __init__(self, resource, field):
        self.resource = resource
        self.field = field

    def set(self, value, **kwargs):
        self.field.on_set(self.resource, value, **kwargs)

    def get(self):
        return getattr(self.resource, self.field.name)

    def compare(self, value):
        return self.field.compare(getattr(self.resource.instance, self.field.name), value)

    def __getattr__(self, name):
        return getattr(self.field, name)


class BoundFields:
    def __init__(self, resource):
        self.resource = resource

    def __iter__(self):
        for field in self.resource._fields.values():
            yield BoundField(self.resource, field)

    def __getitem__(self, name):
        if name in self.resource._fields:
            return BoundField(self.resource, self.resource._fields[name])
        else:
            raise KeyError(name)

    def __getattr__(self, name):
        return self[name]


class BaseResource(metaclass=ResourceMeta):
    __abstract__ = True

    def __init__(self, from_instance=None, **kwargs):
        instance = from_instance

        if instance is None:
            instance = self.model()

        object.__setattr__(self, 'instance', instance)
        object.__setattr__(self, 'dirty', dict())
        object.__setattr__(self, 'fields', BoundFields(self))

        for name, value in kwargs.items():
            setattr(self, name, value)

    def get_id(self):
        return self.instance._resource.id

    @classmethod
    def all(cls, *args, **kwargs):
        return [ cls(from_instance=i) for i in cls.model.query.all(*args, **kwargs) ]

    @classmethod
    def get(cls, *args, **kwargs):
        return cls(from_instance=cls.model.query.get(*args, **kwargs))

    @classmethod
    def filter_by(cls, *args, **kwargs):
        return [ cls(from_instance=i) for i in cls.model.query.filter_by(*args, **kwargs).all() ]

    @classmethod
    def from_statement(cls, *args, **kwargs):
        return [ cls(from_instance=i) for i in cls.model.query.from_statement(*args, **kwargs).all() ]

    def title(self):
        return self.id

    def __getattr__(self, name):
        if name == 'id':
            return self.get_id()

        if name in self.dirty:
            value = self.dirty[name]
        else:
            value = getattr(self.instance, name)

        return self._fields[name].from_storage(value)

    def _set_field(self, name, value):
        self.dirty[name] = value

    def __setattr__(self, name, value):
        self._fields[name].on_set(self, value)

    def save(self):
        for name, value in self.dirty.items():
            setattr(self.instance, name, value)

        db.session.add(self.instance)
        db.session.commit()

        self.dirty.clear()

@event.listens_for(db.session, 'transient_to_pending')
def object_added(session, obj):
    print('Event', obj)

    for c in resource_classes:
        if isinstance(obj, c.model):
            break
    else:
        return

    from crm.models import Resource
    resource = Resource.from_instance(c(from_instance=obj))
    session.add(resource)
