from crm.db import db

import inspect
from flask_sqlalchemy.model import DefaultMeta

from enum import Enum
from werkzeug.security import check_password_hash, generate_password_hash

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Field:
    def __init__(self, column_type, *args, widget=None, **kwargs):
        self.name = None
        self.resource = None
        self.widget = widget
        self.column_type = column_type
        self.column = db.Column(column_type, *args, **kwargs)

    def to_storage(self, value):
        return value

    def from_storage(self, value):
        return value

    def compare(self, stored, value):
        return stored == value

    def _assign(self, name, resource):
        self.name = name
        self.resource = resource

def text_widget():
    pass

def password_widget():
    pass

class TextField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = text_widget

        super().__init__(db.String, *args, widget=widget, **kwargs)


class PasswordField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = password_widget

        super().__init__(db.String, *args, widget=widget, **kwargs)

    def to_storage(self, password):
        return generate_password_hash(password)

    def from_storage(self, hash):
        return '*******'

    def compare(self, hash, password):
        return check_password_hash(hash, password)


class ChoiceField(Field):
    def __init__(self, variants, *args, **kwargs):
        self.variants = variants

        if 'widget' not in kwargs:
            kwargs['widget'] = None
        
        super().__init__(db.String, *args, **kwargs)

    def to_storage(self, value):
        if isinstance(value, Enum) and issubclass(self.variants, Enum):
            return value.value
        elif isinstance(value, str) and isinstance(self.variants, list):
            if value in self.variants:
                return value
            else:
                raise ValueError(f'Invalid variant "{value}"')
        else:
            raise ValueError(f'Unknown variant "{value}"')


    def from_storage(self, value):
        if issubclass(self.variants, Enum):
            return self.variants(value)
        else:
            return value


def isfield(value):
    print(value)
    return isinstance(value, Field)


class ResourceMeta(type):
    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)

    def __new__(cls, clsname, bases, d):
        fields = dict()

        inst = super(ResourceMeta, cls).__new__(cls, clsname, bases, d)

        model_dict = dict(
            id = db.Column(db.Integer, primary_key=True)
        )

        for name, value in vars(inst).items():
            if not isinstance(value, Field):
                continue

            model_dict[name] = value.column
            value._assign(name, inst)
            fields[name] = value

        for field in fields.values():
            delattr(inst, field.name)

        model = DefaultMeta(clsname, (db.Model,), model_dict)

        setattr(inst, 'model', model)
        setattr(inst, '_fields', fields)
        print(inst)

        return inst


class BoundField:
    def __init__(self, resource, field):
        self.resource = resource
        self.field = field

    def set(self, value):
        setattr(self.resource, self.field.name, value)

    def get(self):
        return getattr(self.resource, self.field.name)

    def compare(self, value):
        return self.field.compare(getattr(self.resource.instance, self.field.name), value)


class BoundFields:
    def __init__(self, resource):
        self.resource = resource

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

    def __getattr__(self, name):
        if name == 'id':
            return self.instance.id

        if name in self.dirty:
            value = self.dirty[name]
        else:
            value = getattr(self.instance, name)

        return self._fields[name].from_storage(value)

    def __setattr__(self, name, value):
        self.dirty[name] = self._fields[name].to_storage(value)

    def save(self):
        for name, value in self.dirty.items():
            setattr(self.instance, name, value)

        db.session.add(self.instance)
        db.session.commit()

        self.dirty.clear()
