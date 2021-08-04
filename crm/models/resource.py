from crm.db import db
from crm.access import AccessControlList
from crm.fields import Field

from sqlalchemy import event
from flask_sqlalchemy.model import DefaultMeta
from flask import session


class ResourceUserAssignment(db.Model):
    __tablename__ = 'resource_user'

    user_id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), primary_key=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_at = db.Column(db.DateTime)


class ResourceModelBase(db.Model):
    __abstract__ = True

    @classmethod
    def get_resource(cls, id):
        resource = cls.query.get(id)

        if resource is None:
            return None

        for c in cls.__metaclass__.__variant_classes__:
            column_name = c.model.__tablename__ + '_id'
            id = getattr(resource, column_name)

            if id is not None:
                return c.get(id)

        raise Exception('invalid resource')

    @classmethod
    def from_instance(cls, obj):
        for c in cls.__metaclass__.__variant_classes__:
            if not isinstance(obj, c):
                continue

            columns = dict()
            columns[c.model.__tablename__] = obj.instance

            return cls(**columns)

        raise ValueError('not an instance of a known resource class')

    @classmethod
    def get_type(cls, name):
        for c in cls.__metaclass__.__variant_classes__:
            if name.lower() == c.__name__.lower():
                return c

        return None

    @classmethod
    def on_transient_to_pending(cls, session, obj):
        for c in cls.__metaclass__.__variant_classes__:
            if isinstance(obj, c.model):
                break
        else:
            return

        from crm.models import Resource
        resource = Resource.from_instance(c(from_instance=obj))
        session.add(resource)


class ResourceMeta(type):
    __variant_classes__ = []

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

        cls.__variant_classes__.append(inst)

        model = DefaultMeta(clsname, (db.Model,), model_dict)

        setattr(inst, 'model', model)
        setattr(inst, '_fields', fields)

        return inst

    def create_resource_table(cls):
        properties = dict(
            id = db.Column(db.Integer, primary_key=True),
            __metaclass__ = cls,
        )

        for cls in cls.__variant_classes__:
            column_name = cls.model.__tablename__ + '_id'
            properties[column_name] = db.Column(db.Integer, db.ForeignKey(getattr(cls.model, 'variant_id')))
            properties[cls.model.__tablename__] = db.relationship(cls.model, back_populates='_resource', foreign_keys='Resource.'+column_name)

        resource_cls = DefaultMeta('Resource', (ResourceModelBase,), properties)

        event.listen(db.session, 'transient_to_pending', resource_cls.on_transient_to_pending)

        return resource_cls


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

