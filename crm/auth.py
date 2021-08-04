import functools
from flask import session, redirect, flash, url_for

from crm.models.user import User, UserRole


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
    return User.get(session['user_id'])


def has_role(role):
    if isinstance(role, str):
        role = UserRole(role)

    if 'user_id' not in session:
        return False

    user = User.get(session['user_id'])

    return user is not None and user.role == role
