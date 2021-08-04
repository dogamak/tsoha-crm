from crm.db import db
from crm.access import AccessType, AccessControlList, AccessControlGroup

import inspect
from sqlalchemy import event
from sqlalchemy.orm import declared_attr
from flask_sqlalchemy.model import DefaultMeta
from flask import session

from enum import Enum
from werkzeug.security import check_password_hash, generate_password_hash


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


def isfield(value):
    print(value)
    return isinstance(value, Field)


resource_classes = []


class ResourceUserAssignment(db.Model):
    __tablename__ = 'resource_user'

    user_id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), primary_key=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_at = db.Column(db.DateTime)


def create_resource_table():
    properties = dict(
        id = db.Column(db.Integer, primary_key=True),
    )

    for cls in resource_classes:
        column_name = cls.model.__tablename__ + '_id'
        properties[column_name] = db.Column(db.Integer, db.ForeignKey(getattr(cls.model, 'variant_id')))
        properties[cls.model.__tablename__] = db.relationship(cls.model, back_populates='_resource', foreign_keys='Resource.'+column_name)

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

    def get_type(name):
        for c in resource_classes:
            if name.lower() == c.__name__.lower():
                return c

        return None
        
    setattr(cls, 'get_resource', get_resource)
    setattr(cls, 'from_instance', from_instance)
    setattr(cls, 'get_type', get_type)

    return cls


class ResourceMeta(type):
    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)

    def __new__(cls, clsname, bases, d):
        fields = dict()

        inst = super(ResourceMeta, cls).__new__(cls, clsname, bases, d)

        if d.get('__abstract__', False):
            return inst

        created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        deleted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        variant_id = db.Column('id', db.Integer, primary_key=True)

        model_dict = dict(
            variant_id = variant_id,
            created_by_id = created_by_id,
            deleted_by_id = deleted_by_id,
            created_by = db.relationship('User', foreign_keys=[created_by_id], uselist=False),
            deleted_by = db.relationship('User', foreign_keys=[deleted_by_id], uselist=False),
            _resource = db.relationship('Resource', foreign_keys='Resource.' + inst.__name__.lower() + '_id', uselist=False),
            assigned_users = db.relationship(
                'User',
                secondary='join(Resource, ResourceUserAssignment)',
                primaryjoin=f'{inst.__name__}.variant_id == Resource.{inst.__name__.lower()}_id',
                secondaryjoin='ResourceUserAssignment.user_id == User.variant_id',
                uselist=True,
            ),
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

    def check_access(self, access_type):
        from crm.models import User
        user = User.get(session['user_id'])
        return self.field.check_access(self.resource, user, access_type)

    def __getattr__(self, name):
        return getattr(self.field, name)


class BoundFields:
    def __init__(self, resource):
        self.resource = resource

    def __iter__(self):
        from crm.models import User
        user = User.get(session['user_id'])

        for field in self.resource._fields.values():
            yield BoundField(self.resource, field)

    def __getitem__(self, name):
        if name in self.resource._fields:
            return BoundField(self.resource, self.resource._fields[name])
        else:
            raise KeyError(name)

    def __getattr__(self, name):
        return self[name]


class Section:
    def __init__(self, label, fields):
        self.label = label
        self.fields = fields


class BaseResource(metaclass=ResourceMeta):
    __abstract__ = True
    __acl__ = None
    __layout__ = None

    def __init__(self, from_instance=None, **kwargs):
        instance = from_instance

        if instance is None:
            instance = self.model()

        object.__setattr__(self, 'instance', instance)
        object.__setattr__(self, 'dirty', dict())
        object.__setattr__(self, 'fields', BoundFields(self))

        if self.__acl__ is None:
            object.__setattr__(self, '__acl__', AccessControlList('r=sAaOg,w=sAaO,d=Oa,c=o'))

        for name, value in kwargs.items():
            setattr(self, name, value)

    @property
    def layout(self):
        if self.__layout__ is None:
            yield Section(None, self.fields)
        else:
            for section in self.__layout__:
                yield Section(section.label, [ BoundField(self, field) for field in section.fields ])

    def get_id(self):
        return self.instance._resource.id

    def set_created_by(self, user):
        self._set_field('created_by', user.instance)

    @property
    def created_by(self):
        from crm.models import User
        return User(from_instance=self.instance.created_by)

    @property
    def assigned_users(self):
        from crm.models import User
        return [ User(from_instance=i) for i in self.instance.assigned_users ]

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
        return self.__class__.__name__ + ' #' + self.id

    def check_access(self, user, access_type):
        return self.__acl__.check(self, user, access_type)

    def __eq__(self, other):
        return self.instance.variant_id == other.instance.variant_id

    def __getattr__(self, name):
        if name == 'id':
            return self.get_id()

        if name == 'created_by':
            from crm.models import User
            return User(from_instance=self.instance.created_by)

        if name in self.dirty:
            value = self.dirty[name]
        else:
            value = getattr(self.instance, name)

        try:
            return self._fields[name].from_storage(value)
        except KeyError:
            return getattr(self.instance, name)

    def _set_field(self, name, value):
        self.dirty[name] = value

    def __setattr__(self, name, value):
        self._fields[name].on_set(self, value)

    def assign_to(self, user):
        from crm.models import User
        if isinstance(user, User):
            user = user.instance

        secondary = ResourceUserAssignment(user_id=user.variant_id, resource_id=self.id)
        db.session.add(secondary)
        db.session.commit()

    def unassign_from(self, user):
        from crm.models import User
        if isinstance(user, User):
            user = user.instance

        ResourceUserAssignment.query.filter_by(user_id=user.variant_id, resource_id=self.id).delete()
        db.session.commit()

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
