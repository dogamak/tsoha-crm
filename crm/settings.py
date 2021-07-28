from flask import Blueprint, render_template, request, redirect, flash, url_for

import crm.db
from crm.auth import require_role
from crm.models.user import User, UserRole

blueprint = Blueprint('settings', __name__)

@blueprint.route('/settings')
def settings():
    return render_template('settings.html')

@blueprint.route('/settings/users')
@require_role(UserRole.Administrator)
def user_management():
    users = User.query.all()

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

    if User.query.filter_by(username=username).first() is not None:
        flash(f'User with username "{username}" already exists.', 'error')
        return redirect(url_for('settings.create_user'))

    user = User(username=username, role=role)
    user.set_password(request.form['password'])

    db = crm.db.get_db()
    db.session.add(user)
    db.session.commit()

    flash(f'User @{username} created successfully.', 'success')
    return redirect(url_for('settings.create_user'))
