import json
from flask import Blueprint, redirect, url_for, render_template, flash, request, session
from datetime import datetime
from dataclasses import dataclass

from crm.fields import ActionContext
from crm.access import AccessType
from crm.models import Resource, User
from crm.auth import get_session_user, require_auth, check_csrf
from crm.utils import generate_random_string
from crm.db import db


blueprint = Blueprint('resource', __name__) 


class EditSession:
    def __init__(self, key, resource, created_by, form_url=None, finished_url=None):
        self.resource = resource
        self.resource_type = resource.__class__
        self.resource_id = resource.id
        self.edit_state = resource.staged
        self.key = key
        self.created_at = datetime.now()
        self.created_by = created_by
        self._form_url = form_url
        self._finished_url = finished_url
        self.commit_ctx = resource.create_commit_context()

    def reset_context(self):
        self.commit_ctx = self.resource.create_commit_context()

    def validate(self):
        self.commit_ctx.validate()

    def commit(self):
        if self.resource_id is None:
            instance = self.resource_type()
        else:
            instance = Resource.get_resource(self.resource_id)

        instance = self.resource_type(from_instance=instance.instance, state=self.edit_state)
        self.resource = instance

        instance.save(self.commit_ctx)

        if len(self.commit_ctx.exceptions) > 0:
            return False

        self.__class__.sessions.pop(self.key)

        return True

    @property
    def form_url(self):
        if self._form_url is not None:
            return self._form_url

        if self.resource_id is None:
            return url_for('resource.create', type=self.resource_type.__name__, key=self.key)
        else:
            return url_for('resource.edit', id=self.resource_id, key=self.key)

    @property
    def finished_url(self):
        if self._finished_url is not None:
            return self._finished_url

        return url_for('resource.view', id=self.resource.id)

    @classmethod
    def create(cls, resource, **kwargs):
        while True:
            key = generate_random_string(16)

            if key not in cls.sessions:
                break

        editing_session = cls(key, resource, session['user_id'], **kwargs)
        cls.sessions[key] = editing_session

        return editing_session

    @classmethod
    def get(cls, key):
        if key not in cls.sessions:
            return None
        
        edit_session = cls.sessions[key]

        if session['user_id'] != edit_session.created_by:
            return None

        if edit_session.resource_id is None:
            instance = edit_session.resource_type()
        else:
            instance = Resource.get_resource(edit_session.resource_id)

        instance = edit_session.resource_type(from_instance=instance.instance, state=edit_session.edit_state)

        edit_session.resource = instance # edit_session.resource_type(state=edit_session.edit_state)
        # db.session.refresh(edit_session.resource.instance)
        # db.session.add(edit_session.resource.instance)

        return edit_session


EditSession.sessions = dict()


@blueprint.route('/view/<id>')
@require_auth
def view(id):
    resource = Resource.get_resource(id)

    if not resource.check_access(get_session_user(), AccessType.Read):
        return redirect(url_for('dashboard'))

    return render_template(
        'view-resource.html',
        resource=resource,
        users=json.dumps([
            { "id": user.id, "title": user.title(), "type": "User" }
            for user in User.all()
            if user not in resource.assigned_users
        ]),
    )

@blueprint.route('/edit/<id>/assign', methods=['POST'])
@check_csrf
@require_auth
def assign(id):
    resource = Resource.get_resource(id)
    user = Resource.get_resource(request.form['user'])

    if not resource.check_access(get_session_user(), AccessType.Write):
        return redirect(url_for('dashboard'))

    resource.assign_to(user)
    return redirect(url_for('resource.view', id=resource.id))

@blueprint.route('/edit/<resource_id>/unassign/<user_id>')
@check_csrf
@require_auth
def unassign(resource_id, user_id):
    resource = Resource.get_resource(resource_id)
    user = Resource.get_resource(user_id)

    if not resource.check_access(get_session_user(), AccessType.Write):
        return redirect(url_for('dashboard'))

    resource.unassign_from(user)
    return redirect(url_for('resource.view', id=resource.id))


@blueprint.route('/edit/<id>')
@require_auth
def begin_edit(id):
    resource = Resource.get_resource(id)

    if not resource:
        return redirect(url_for('dashboard'))

    session = EditSession.create(resource)

    return redirect(session.form_url)


@dataclass
class FieldMessage:
    type: str
    text: str


@blueprint.route('/edit/<id>/<key>')
@require_auth
def edit(id, key):
    edit_session = EditSession.get(key)

    if edit_session is None:
        return redirect(url_for('resource.begin_edit', id=id))

    if not edit_session.resource.check_access(get_session_user(), AccessType.Write):
        return redirect(url_for('dashboard'))

    field_messages = {}
    messages = []

    for exception in edit_session.commit_ctx.exceptions:
        msg = FieldMessage(type='danger', text=exception.message)

        if exception.field is None:
            messages.append(msg)
        else:
            if exception.field.name not in field_messages:
                field_messages[exception.field.name] = []

            field_messages[exception.field.name].append(msg)

    return render_template(
        'edit-resource.html',
        edit_session=edit_session,
        messages=messages,
        field_messages=field_messages,
        AccessType=AccessType,
    )

@blueprint.route('/commit/<key>', methods=['POST'])
@check_csrf
@require_auth
def commit_edit(key):
    edit_session = EditSession.get(key)

    if edit_session is None:
        return render_template('not_found.html')

    if not edit_session.resource.check_access(get_session_user(), AccessType.Write):
        return redirect(url_for('dashboard'))
    
    edit_session.reset_context()

    for field in edit_session.resource.fields:
        if field.name not in request.files and field.name not in request.form:
            continue

        ctx = ActionContext(field, edit_session)
        field.set_value_action(ctx)
    
    action = request.form.get('__action', None)
    result = None

    if action is not None:
        field_name, action_name = action.split('.', 1)
        field = edit_session.resource.fields[field_name]
        attr = getattr(field, action_name)

        if not hasattr(attr, '__is_action'):
            flash('Invalid request.')
            return redirect(edit_session.form_url)

        ctx = ActionContext(field, edit_session)
        result = attr(ctx)

        edit_session.validate()
    else:
        edit_session.validate()

        if len(edit_session.commit_ctx.exceptions) == 0:
            success = edit_session.commit()

            if len(edit_session.commit_ctx.exceptions) == 0:
                flash('Resource updated successfully!')
                result = redirect(edit_session.finished_url)

    if result is None:
        result = redirect(edit_session.form_url)

    return result


@blueprint.route('/create/<type>')
@require_auth
def begin_create(type):
    resource_type = Resource.get_type(type)

    default_values = resource_type()
    default_values.set_created_by(get_session_user())

    session = EditSession.create(default_values)

    if not default_values.check_access(get_session_user(), AccessType.Create):
        return redirect(url_for('dashboard'))

    return redirect(session.form_url)

@blueprint.route('/confirm/<key>')
@require_auth
def confirm_edit(key):
    edit_session = EditSession.get(key)

    if edit_session is None:
        return render_template('not_found.html')

    return


@blueprint.route('/create/<type>/<key>')
@require_auth
def create(type, key):
    edit_session = EditSession.get(key)

    if edit_session is None:
        return redirect(url_for('resource.begin_create', type=type))

    if not edit_session.resource.check_access(get_session_user(), AccessType.Create):
        return redirect(url_for('dashboard'))

    edit_session.resource.set_created_by(get_session_user())

    field_messages = {}
    messages = []

    for exception in edit_session.commit_ctx.exceptions:
        msg = FieldMessage(type='danger', text=exception.message)

        if exception.field is None:
            messages.append(msg)
        else:
            if exception.field.name not in field_messages:
                field_messages[exception.field.name] = []

            field_messages[exception.field.name].append(msg)

    return render_template(
        'create-resource.html',
        type=type,
        edit_session=edit_session,
        resource=edit_session.resource,
        messages=messages,
        field_messages=field_messages
    )
