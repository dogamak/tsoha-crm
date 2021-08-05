import json
from flask import Blueprint, redirect, url_for, render_template, flash, request, session

from crm.access import AccessType
from crm.models import Resource, User
from crm.auth import get_session_user

blueprint = Blueprint('resource', __name__) 

@blueprint.route('/view/<id>')
def view(id):
    resource = Resource.get_resource(id)

    if not resource.check_access(get_session_user(), AccessType.Read):
        return render_template('not_found')

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
def assign(id):
    resource = Resource.get_resource(id)
    user = Resource.get_resource(request.form['user'])

    if not resource.check_access(get_session_user(), AccessType.Write):
        return render_template('not_found')

    resource.assign_to(user)
    return redirect(url_for('resource.view', id=resource.id))

@blueprint.route('/edit/<resource_id>/unassign/<user_id>')
def unassign(resource_id, user_id):
    resource = Resource.get_resource(resource_id)
    user = Resource.get_resource(user_id)

    if not resource.check_access(get_session_user(), AccessType.Write):
        return render_template('not_found')

    resource.unassign_from(user)
    return redirect(url_for('resource.view', id=resource.id))

@blueprint.route('/edit/<id>')
def edit(id):
    resource = Resource.get_resource(id)

    if not resource.check_access(get_session_user(), AccessType.Write):
        return render_template('not_found')

    return render_template('edit-resource.html', resource=resource, AccessType=AccessType)

@blueprint.route('/edit/<id>', methods=['POST'])
def edit_post(id):
    resource = Resource.get_resource(id)

    if resource is None:
        return redirect(url_for('not_found'))

    if not resource.check_access(get_session_user(), AccessType.Write):
        return render_template('not_found')

    for field in resource.fields:
        if field.name in request.files:
            new_value = request.files[field.name]
        elif field.name in request.form:
            new_value = request.form[field.name]
        else:
            continue

        extra_arguments = {
            param_name.split('.', 1)[1]: param_value
            for param_name, param_value in request.form.items()
            if param_name.startswith(field.name + '.')
        }

        try:
            field.set(new_value, **extra_arguments)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('resource.view', id=resource.id))
    
    resource.save()

    flash('Resource updated successfully!')
    return redirect(url_for('resource.view', id=resource.id))

@blueprint.route('/create/<type>')
def create(type):
    resource_type = Resource.get_type(type)
    default_values = resource_type()

    if not default_values.check_access(get_session_user(), AccessType.Create):
        return render_template('not_found')

    return render_template('create-resource.html', type=type, resource=default_values)

@blueprint.route('/create/<type>', methods=['POST'])
def create_post(type):
    resource = Resource.get_type(type)()

    if not resource.check_access(get_session_user(), AccessType.Create):
        return render_template('not_found')

    user = get_session_user()
    resource.set_created_by(user)

    for field in resource.fields:
        if field.name in request.files:
            new_value = request.files[field.name]
        elif field.name in request.form:
            new_value = request.form[field.name]
        else:
            continue

        extra_arguments = {
            param_name.split('.', 1)[1]: param_value
            for param_name, param_value in request.form.items()
            if param_name.startswith(field.name + '.')
        }

        try:
            field.set(new_value, **extra_arguments)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('resource.create', type=type))
    
    resource.save()

    flash('Resource created successfully!')
    return redirect(url_for('resource.view', id=resource.id))
