import functools
from flask import request, session, redirect, flash, url_for

from crm.models.user import User, UserRole
from crm.utils import generate_random_string


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


def get_session_user():
    return User.get(session['user_id']) if 'user_id' in session else None


def check_csrf(handler):
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        current_csrf = session.get('CSRF')
        provided_csrf = request.form.get('__CSRF') or request.args.get('csrf')

        session['CSRF'] = generate_random_string(32)

        if current_csrf is None or provided_csrf is None or provided_csrf != current_csrf:
            return redirect(url_for('dashboard'))

        return handler(*args, **kwargs)

    return wrapper


def has_role(role):
    if isinstance(role, str):
        role = UserRole(role)

    if 'user_id' not in session:
        return False

    user = User.get(session['user_id'])

    return user is not None and user.role == role
