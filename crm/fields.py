from dataclasses import dataclass
from enum import Enum
from flask import request, redirect
from sqlalchemy.sql import update, select
from werkzeug.security import check_password_hash, generate_password_hash
import babel.numbers
import json
import sqlalchemy

from sqlalchemy.sql import select, not_

from crm.db import db
from crm.access import AccessControlList
from crm.mutation import DecoratorMutation, Mutation, mutation


class ActionContext:
    def __init__(self, bound, edit_session):
        self.bound = bound
        self.arguments = ActionArguments(self)
        self.edit_session = edit_session

    def dispatch(self, mutation):
        self.bound.resource.stage_mutation(mutation)

    @property
    def value(self):
        name = self.bound.name

        if name in request.form:
            return request.form[name]
        elif name in request.files:
            return request.files[name]
        
        return None


class ActionArguments:
    def __init__(self, ctx):
        self.ctx = ctx

    def __getitem__(self, name):
        name = self.ctx.bound.name + '.' + name

        if name in request.form:
            return request.form[name]
        elif name in request.files:
            return request.files[name]
        
        return None

    def __getattr__(self, name):
        return self[name]


def action(func):
    func.__is_action = True
    return func


class FieldState:
    def __init__(self):
        self.mutations = []

    def stage_mutation(self, mutation):
        self.mutations.append(mutation)

    def get_mutations(self, bound):
        value = bound.get_persisted_value()

        i = 0

        while len(self.mutations) > i:
            mutation = self.mutations[i]

            print(mutation, mutation.args[0], value, type(mutation.args[0]), type(value), mutation.args[0] == value)

            if isinstance(mutation, DecoratorMutation) and mutation.attr.name == 'set_value' and mutation.args[0] == value:
                self.mutations.pop(i)
                continue

            i += 1

        return self.mutations

    def clear(self):
        self.mutations = []

    def is_dirty(self):
        return len(self.mutations) > 0

    def get_value(self, bound):
        for mutation in self.mutations[::-1]:
            if mutation.type == Field.set_value:
                return mutation.args[0]

        return bound.get_persisted_value()


class SetMutation(Mutation):
    def __init__(self, field, value):
        super().__init__(field)
        self.value = value

    def commit(self, resource):
        setattr(resource.instance, self.field.name, self.value)

    def describe(self):
        return f'Change field "{self.field.label}" to "{self.value}"'


def action(func):
    func.__is_action = True
    return func


class Field:
    def __init__(self, column_type, *args, label=None, widget=None, acl=None, **kwargs):
        self.name = None
        self.resource = None
        self.label = label
        self.widget = widget
        self.column_type = column_type
        self.acl = acl or AccessControlList()
        self.column_args = args
        self.column_kwargs = kwargs
        self.state = FieldState

    def execute_action(self, name, *args, **kwargs):
        member = getattr(self, name)

        if not hasattr(member, '__is_action'):
            raise ValueError(f'No such action for field type {self.__class__.__name__}: {name}')

        return member(*args, **kwargs)

    def create_columns(self):
        if self.column_type is None:
            return []

        return [ db.Column(self.column_type, *self.column_args, **self.column_kwargs) ]

    @property
    def column(self):
        return getattr(self.resource.model, self.name)

    def check_access(self, resource, user, access_type):
        return self.acl.check(resource, user, access_type)

    def retrieve(self, resource):
        return getattr(resource.instance, self.name)

    def to_storage(self, value):
        return value

    def from_storage(self, value):
        return value

    def compare(self, stored, value):
        return stored == value

    @mutation
    def set_value(self, ctx, value):
        setattr(ctx.resource.instance, self.name, value)

    @action
    def set_value_action(self, ctx):
        ctx.dispatch(self.set_value(ctx.value))

    @set_value.describe
    def describe_set_value(self, value):
        return f'Change field "{self.label}" to "{value}".'

    def get_persisted_value(self, resource):
        return self.from_storage(self.retrieve(resource))

    def get_value(self, bound):
        return bound.state.get_value(bound)

    def _assign(self, name, resource):
        self.name = name
        self.resource = resource

        if self.label is None:
            self.label = ' '.join(part[0].upper() + part[1:] for part in name.split('_'))



class TextField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = 'text'

        super().__init__(db.String, *args, widget=widget, **kwargs)

    def from_storage(self, value):
        if value is None:
            return ''

        return value


class DateField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = 'date'

        super().__init__(db.DateTime, *args, widget=widget, **kwargs)

    @action
    def set_value_action(self, ctx):
        value = ctx.value

        if value == '':
            value = None

        ctx.dispatch(self.set_value(value))


@dataclass(eq=True)
class CurrencyValue:
    amount: float
    currency: str

    def __str__(self):
        return babel.numbers.format_currency(self.amount, self.currency)


class CurrencyField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = 'currency'

        super().__init__(None, *args, widget=widget, **kwargs)

    def create_columns(self):
        return [
            db.Column(self.name + '_amount', db.Integer),
            db.Column(self.name + '_currency', db.String),
        ]

    def retrieve(self, resource):
        return CurrencyValue(getattr(resource.instance, self.name), getattr(resource.instance, self.name + '_1'))

    @mutation
    def set_value(self, ctx, value):
        setattr(ctx.resource.instance, self.name, value.amount)
        setattr(ctx.resource.instance, self.name + '_1', value.currency)

    @set_value.describe
    def describe_set_value(self, value):
        return f'Set field "{self.label}" to {value}'

    @action
    def set_value_action(self, ctx):
        amount = float(ctx.value)
        currency = ctx.arguments['currency']
        mutation = self.set_value(CurrencyValue(amount, currency))
        ctx.dispatch(mutation)

    def list_currencies(self):
        return babel.numbers.list_currencies()


class PasswordField(Field):
    def __init__(self, *args, widget=None, **kwargs):
        if widget is None:
            widget = 'password'

        super().__init__(db.String, *args, widget=widget, **kwargs)

    def to_storage(self, password):
        return generate_password_hash(password)

    def from_storage(self, hash):
        return '*******'

    @action
    def set_value_action(self, ctx):
        password = ctx.value
        confirmation = ctx.arguments['confirmation']

        if password == '':
            return

        if confirmation is not None and password != confirmation:
            return

        ctx.dispatch(self.set_value(password))

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

    @mutation
    def set_value(self, ctx, file):
        from crm.models import File

        file = File.create_from(file.stream, name=file.filename)
        db.session.add(file)

        setattr(ctx.resource.instance, self.name, file.hash)

    @action
    def set_value_action(self, ctx):
        if ctx.value.filename == '':
            return

        ctx.dispatch(self.set_value(ctx.value))


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

    @action
    def set_value_action(self, ctx):
        from crm.models import Resource

        if isinstance(ctx.value, str):
            value = Resource.get_resource(int(ctx.value))

        ctx.dispatch(self.set_value(value.id))

    def get_options(self):
        return json.dumps([
            { "id": instance.id, "type": self.resource_type.__name__, "title": instance.title() }
            for instance in self.resource_type.all()
        ])


class TableFieldState(FieldState):
    def __init__(self):
        super().__init__()

        self.added = []
        self.removed = []

    def stage_mutation(self, mutation):
        if mutation.type == TableField.add_row:
            id = mutation.args[0]

            if id in self.removed:
                self.removed.remove(id)
            elif id not in self.added:
                self.added.append(id)
            else:
                return

        elif mutation.type == TableField.remove_row:
            id = mutation.args[0]

            if id in self.added:
                self.added.remove(id)
            elif id not in self.removed:
                self.removed.append(id)
            else:
                return

        super().stage_mutation(mutation)

    def get_mutations(self, bound):
        return self.mutations

    def get_value(self, bound):
        variant_column_name = bound.foreign_type.__name__.lower() + '_id'
        resource_model = bound.foreign_type.__resource_model__
        variant_column = getattr(resource_model, variant_column_name)

        added_variant_ids = select(variant_column).where(resource_model.id.in_(self.added))
        removed_variant_ids = select(variant_column).where(resource_model.id.in_(self.removed))

        added_resources = select(bound.foreign_type.model) \
            .where(bound.foreign_type.model.variant_id.in_(added_variant_ids))

        query = bound.get_query(bound) \
            .where(not_(bound.foreign_type.model.variant_id.in_(removed_variant_ids))) \
            .union(added_resources)

        query = db.session.query(bound.foreign_type.model).from_statement(query)

        return [
            bound.foreign_type(from_instance=row[0])
            for row in db.session.execute(query).all()
        ]


class TableField(Field):
    def __init__(self, foreign_field, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = 'table'

        self._foreign_field_ref = foreign_field
        self._foreign_field = None

        super().__init__(None, *args, **kwargs)

        self.state = TableFieldState

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

    @action
    def create_new(self, ctx):
        from crm.views.resource import EditSession
        session = EditSession.create(self.foreign_type(), finished_url=ctx.edit_session.form_url)
        session.resource.fields[self.foreign_field.name].set(ctx.bound.resource.id)
        return redirect(session.form_url)

    @action
    def remove_selected(self, ctx):
        if ctx.arguments['selected'] == '':
            return

        selected = ctx.arguments['selected'].split(',')

        for id in selected:
            ctx.dispatch(self.remove_row(id))

    @mutation
    def remove_row(self, ctx, id):
        from crm.models import Resource
        resource = Resource.get_resource(id)
        resource.fields[self.foreign_field.name].set(None)
        resource.save()

    @remove_row.describe
    def describe_remove_row(self, id):
        from crm.models import Resource
        resource = Resource.get_resource(id)
        return f'Remove "{resource.title()}" from "{self.label}".'

    @mutation
    def add_row(self, ctx, id):
        pass

    def persist(self, resource, cache):
        pass

    def retrieve(self, resource):
        if resource.id is None:
            return []

        return [
            self.foreign_field.resource(from_instance=i)
            for i in self.foreign_type.model.query.filter(self.foreign_field.column == resource.id).all()
        ]

    def get_query(self, bound):
        if bound.resource.id is None:
            return select(self.foreign_type.model).where(sqlalchemy.sql.false())

        return select(self.foreign_type.model).where(self.foreign_field.column == bound.resource.id)

    @staticmethod
    def get_value_json(bound):
        return json.dumps([
            { "id": row.id, "title": row.title() }
            for row in bound.get()
        ])
