from crm.db import db
from crm.access import AccessControlList
from crm.fields import Field

from sqlalchemy import event
from flask_sqlalchemy.model import DefaultMeta
from flask import session


class ResourceUserAssignment(db.Model):
    """
    A secondary join table which represents a many-to-many relationship between resources and users.
    """

    __tablename__ = 'resource_user'

    user_id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), primary_key=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_at = db.Column(db.DateTime)


class ResourceModelBase(db.Model):
    """
    Base class for the database table model which combines all the
    different types of resources using foreign key references.
    """

    # This tells SQLAlchemy that this class is not a concrete database model.
    __abstract__ = True

    @classmethod
    def get_resource(cls, id):
        """
        Fetches a resource from the database based on it's ID and wraps
        it in a class appropriate for it's resource type.
        """

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
        """
        Wraps an SQLAlchemy object in an appropriate resource subclass.
        """

        for c in cls.__metaclass__.__variant_classes__:
            if not isinstance(obj, c):
                continue

            columns = dict()
            columns[c.model.__tablename__] = obj.instance

            return cls(**columns)

        raise ValueError('not an instance of a known resource class')

    @classmethod
    def get_type(cls, name):
        """
        Returns a subclass of the resource base class associated with a given resource type name.
        """

        for c in cls.__metaclass__.__variant_classes__:
            if name.lower() == c.__name__.lower():
                return c

        return None

    @classmethod
    def on_transient_to_pending(cls, session, obj):
        """
        An event hook which SQLAlchemy calls whenever a new object is being inserted into the database.
        """

        # Check if the inserted object is a subclass of the resource base class
        for c in cls.__metaclass__.__variant_classes__:
            if isinstance(obj, c.model):
                break
        else:
            return

        # If so, create a new `resource` row which links the object to be inserted to it's resource ID
        from crm.models import Resource
        resource = Resource.from_instance(c(from_instance=obj))
        session.add(resource)


class ResourceMeta(type):
    """
    Metaclass for the resource base class.
    """

    __variant_classes__ = []

    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)

    def __new__(cls, clsname, bases, d):
        # This method is called every time this metaclass is used to construct a new class

        fields = dict()

        # Instantiate the new class. The name `inst` refers to the value being an
        # instance of this metaclass (opposed to `cls`), not an instance of the
        # class we are constructing.
        inst = super(ResourceMeta, cls).__new__(cls, clsname, bases, d)

        # Exit early if we are constructing the base class itself
        if d.get('__abstract__', False):
            return inst

        # The next segment of code constructs a SQLAlchemy database model class dynamically
        # based on the class attributes of the subclass we are currently constructing

        # First, we define some columns which are referenced by the other columns

        created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        deleted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        variant_id = db.Column('id', db.Integer, primary_key=True)

        # Thses columns are present on tables of every resource type

        model_dict = dict(
            variant_id = variant_id,
            created_by_id = created_by_id,
            deleted_by_id = deleted_by_id,
            created_by = db.relationship('User', foreign_keys=[created_by_id], uselist=False),
            deleted_by = db.relationship('User', foreign_keys=[deleted_by_id], uselist=False),
            _resource = db.relationship('Resource', foreign_keys='Resource.' + inst.__name__.lower() + '_id', uselist=False),

            # This relationship represents the list of users who have been assigned to a particular resource.
            # It involves four tables (<Resource Variant Table> -> Resource -> ResourceUserAssignment -> User)
            # and as such is a bit cumbersome to write.  It is essentially just an ordinary many-to-many
            # join, but instead of an normal materialized junction table, a join between the Resource
            # and ResourceUserAssignment tables is used.
            assigned_users = db.relationship(
                'User',
                secondary='join(Resource, ResourceUserAssignment)',
                primaryjoin=f'{inst.__name__}.variant_id == Resource.{inst.__name__.lower()}_id',
                secondaryjoin='ResourceUserAssignment.user_id == User.variant_id',
                uselist=True,
            ),
        )

        # Next, we iterate through the class attributes of `inst` and process
        # all attributes which have a value subclassing the `Field` type.

        for name, value in vars(inst).items():
            if not isinstance(value, Field):
                continue

            column = value.create_column()

            if column is not None:
                model_dict[name] = column

            value._assign(name, inst)
            fields[name] = value

        # The for loop below removes the processed class attributes from the class.
        # If the were left present, our `__getattr__` and `__setattr__` implementations
        # found not be called when accessing them.

        for field in fields.values():
            delattr(inst, field.name)

        # Add this new subclass to the list of subclasses 
        cls.__variant_classes__.append(inst)

        # Instantiate the SQLAlchemy Model sub-class using the class attributes from `model_dict`
        model = DefaultMeta(clsname, (db.Model,), model_dict)

        # Assigne the list of processed `Field` types, and the Model class created above,
        # to the new resource subclass.
        setattr(inst, 'model', model)
        setattr(inst, '_fields', fields)
        setattr(inst, '__metaclass__', cls)
        setattr(inst, '__abstract__', False)

        return inst

    def __getattr__(self, name):
        if self.__abstract__:
            raise AttributeError(name)

        return self._fields[name]

    def create_resource_table(cls):
        """
        Creates an SQLAlchemy model for a table, which contains an foreign key column for each of the
        known resource types, as well as an ID column.

        This table can be used to refer to an resource, without having to know it's type. 
        """

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
    """
    Represents an `Field` which is associated with a resource instance.
    This class is essentially an proxy class for `Field` which injects
    the associated resource into appropriate method calls.
    """

    def __init__(self, resource, field):
        self.resource = resource
        self.field = field

    def set(self, value, **kwargs):
        self.field.set_value(self.resource, value, **kwargs)

    def get(self):
        return self.resource._get_field(self)

    def compare(self, value):
        return self.field.compare(getattr(self.resource.instance, self.field.name), value)

    def check_access(self, access_type):
        from crm.models import User
        user = User.get(session['user_id'])
        return self.field.check_access(self.resource, user, access_type)

    def __getattr__(self, name):
        return getattr(self.field, name)


class BoundFields:
    """
    Collection of `Field` object associated with a single resource instance.
    """

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


class Section:
    """
    An optionally labelled section containing a set of fields.
    """

    def __init__(self, label, fields):
        self.label = label
        self.fields = fields


class BaseResource(metaclass=ResourceMeta):
    """ Base parent class for all kinds of resources.

    :param from_instance: If provided, the created instance wraps this underlying database row.
    :type: SQLAlchemy model instance
    """

    __abstract__ = True

    __acl__ = None
    """Access Control List for the resources of this type.

    Defines what permissions particular user has to an
    instance of this resource type.
    """

    __layout__ = None
    """List of Sections containing references to Fields of this Resource.
        
    Used when displaying this resource.  
    """

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
        """The prefered layout in which this resource's field should be displayed.

        If no layout is explicitly specified using the `__layout__` class attribute,
        a default layout is returned.
        """

        if self.__layout__ is None:
            yield Section(None, self.fields)
        else:
            for section in self.__layout__:
                yield Section(section.label, [ BoundField(self, field) for field in section.fields ])

    def get_id(self):
        """
        Returns the ID of this resource.
        """

        if self.instance._resource is not None:
            return self.instance._resource.id
        
        return None

    def set_created_by(self, user):
        """
        Sets the `created_by` metadata field to the specified user.
        """

        self._set_column_raw('created_by', user.instance)

    @property
    def created_by(self):
        """
        User who created this resource.

        For now, this also serves as the "owner" of this resource.
        """

        from crm.models import User
        return User(from_instance=self.instance.created_by)

    @property
    def assigned_users(self):
        """
        List of users to whom this resource has been assigned to.
        """

        from crm.models import User
        return [ User(from_instance=i) for i in self.instance.assigned_users ]

    @classmethod
    def all(cls, *args, **kwargs):
        """
        Fetches all instances of this resource type from the database.

        Wraps a method of the same name from SQLAlchemy.
        """

        return [ cls(from_instance=i) for i in cls.model.query.all(*args, **kwargs) ]

    @classmethod
    def get(cls, *args, **kwargs):
        """
        Fetches a single instance of this resource type from the database,
        based on its resource type dependent internal ID.

        Most likely you will want to use `Resource.get_resource` instead,
        unless you know that a resource can only be of one type in this
        context.
        """

        return cls(from_instance=cls.model.query.get(*args, **kwargs))

    @classmethod
    def filter_by(cls, *args, **kwargs):
        """
        Fetches a list of resources based on specified column values.

        Note that values must be specified in the format they are in-database.
        """

        return [ cls(from_instance=i) for i in cls.model.query.filter_by(*args, **kwargs).all() ]

    @classmethod
    def from_statement(cls, *args, **kwargs):
        """
        Executes an arbitrary SQL statement and wraps it's results into Resource objects of this type.
        """

        return [ cls(from_instance=i) for i in cls.model.query.from_statement(*args, **kwargs).all() ]

    @classmethod
    def resolve_resource(cls, reference):
        parts = reference.split('.')

        if len(parts) not in (1, 2):
            raise ValueError('Invalid reference')

        resource_type = parts[0]

        for vcls in cls.__metaclass__.__variant_classes__:
            if vcls.__name__ == resource_type:
                break
        else:
            raise ValueError('Unknown resource type: ' + resource_type)

        if len(parts) == 1:
            return vcls

        column_name = parts[1]
        return getattr(vcls, column_name)


    def title(self):
        """
        Returns the title of this resource.

        A title should be something a human would want to use to identify
        a resource of this type from a list of many.
        """

        return self.__class__.__name__ + ' #' + str(self.id)

    def check_access(self, user, access_type):
        """
        Returns True if the `user` has access permissions of the
        specified type against this resource.

        :param user: User which is trying to take action against this resource.
        :param access_type: Type of the action the user is trying to perform.

        :returns: True if the user should be allowed to perform the action, False otherwise.
        """

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

    def _set_field(self, field, value):
        if field.name not in self.dirty:
            self.dirty[field.name] = field.cache(self, field)

        self.dirty[field.name].set_value(value)

    def _set_column_raw(self, column, value):
        setattr(self.instance, column, value)

    def _get_field(self, field):
        if field.name not in self.dirty:
            self.dirty[field.name] = field.cache(self, field)

        cache = self.dirty[field.name]

        return field.get_value(self, cache)

    def __setattr__(self, name, value):
        field = self._fields[name]

        if name not in self.dirty:
            self.dirty[name] = field.cache(self, field)

        cache = self.dirty[name]
        field.set_value(self, value)

    def assign_to(self, user):
        """
        Assigns this resource to the specified user.
        """

        from crm.models import User
        if isinstance(user, User):
            user = user.instance

        secondary = ResourceUserAssignment(user_id=user.variant_id, resource_id=self.id)
        db.session.add(secondary)
        db.session.commit()

    def unassign_from(self, user):
        """
        Removes the assignment of this resource from the specified user.
        """

        from crm.models import User
        if isinstance(user, User):
            user = user.instance

        ResourceUserAssignment.query.filter_by(user_id=user.variant_id, resource_id=self.id).delete()
        db.session.commit()

    def save(self):
        """
        Saves this resource to the database and performs the associated book-keeping.
        """

        for name, cache in self.dirty.items():
            self._fields[name].persist(self, cache)

        db.session.add(self.instance)
        db.session.commit()

        self.dirty.clear()

