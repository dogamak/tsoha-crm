from flask import Blueprint, render_template, request, redirect, flash, url_for, session

from crm.auth import require_role, require_auth
from crm.models.user import User, UserRole
from crm.access import AccessType
from crm.views.resource import EditSession

blueprint = Blueprint('settings', __name__)

@blueprint.route('/settings')
def settings():
    return redirect(url_for('settings.edit_profile'))

@blueprint.route('/settings/users')
@require_role(UserRole.Administrator)
def user_management():
    users = User.all()

    return render_template('settings-user-management.html', users=users)

@blueprint.route('/settings/users/create')
@require_role(UserRole.Administrator)
def create_user():
    return render_template('settings-create-user.html')

@blueprint.route('/settings/users/create', methods=['POST'])
@require_role(UserRole.Administrator)
def create_user_post():
    for field in ('role', 'username', 'password', 'password_confirmation'):
        if field not in request.form or request.form[field] == '':
            flash(f'Please fill all required fields.', 'error')
            return redirect(url_for('settings.create_user'))

    username = request.form['username']

    if request.form['password'] != request.form['password_confirmation']:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('settings.create_user'))

    from crm.models.user import User, UserRole

    try:
        role = UserRole(request.form['role'])
    except ValueError:
        flash('Invalid role.', 'error')
        return redirect(url_for('settings.create_user'))

    if len(User.filter_by(username=username)) > 0:
        flash(f'User with username "{username}" already exists.', 'error')
        return redirect(url_for('settings.create_user'))

    user = User(username=username, role=role, password=request.form['password'])
    user.save()

    flash(f'User @{username} created successfully.', 'success')
    return redirect(url_for('settings.create_user'))

@blueprint.route('/settings/profile')
@require_auth
def edit_profile():
    user = User.get(session['user_id'])
    edit_session = EditSession.create(user)
    return render_template("settings-profile.html", edit_session=edit_session, user=user, AccessType=AccessType, messages=[], field_messages={})
