import functools
from flask import Blueprint, render_template, request, session, redirect, flash, url_for

from crm.db import get_db
from crm.models import User

blueprint = Blueprint('auth', __name__)

def require_auth(handler):
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        return handler(*args, **kwargs)

    return wrapper

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
