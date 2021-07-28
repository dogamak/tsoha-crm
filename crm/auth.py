import functools
from flask import Blueprint, render_template, request, session, redirect, flash, url_for

from crm.db import get_db
from crm.models.user import User, UserRole

blueprint = Blueprint('auth', __name__)

def require_auth(handler):
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        return handler(*args, **kwargs)

    return wrapper

def require_role(role):
    def decorator(handler):
        @functools.wraps(handler)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))

            if not has_role(role):
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))

            return handler(*args, **kwargs)

        return wrapper

    return decorator

def has_role(role):
    if isinstance(role, str):
        role = UserRole(role)

    if 'user_id' not in session:
        return False

    user = User.query.get(session['user_id'])

    return user is not None and user.role == role

@blueprint.route('/login')
def login():
    if 'user_id' in session:
        return redirect('/')

    return render_template('login.html')

@blueprint.route('/login', methods=['POST'])
def login_post():
    db = get_db()

    if 'username' not in request.form:
        return ''

    user = User.query.filter_by(username=request.form['username']).first()

    if not user:
        flash('Invalid credentials', 'error')
        return redirect('/login')

    if not user.check_password(request.form['password']):
        flash('Invalid credentials', 'error')
        return redirect('/login')

    session['user_id'] = user.id

    return redirect('/')

@blueprint.route('/logout')
def logout():
    del session['user_id']
    return redirect('/login')
