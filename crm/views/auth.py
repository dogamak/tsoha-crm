from flask import Blueprint, render_template, request, session, redirect, flash, url_for
from crm.models import User

blueprint = Blueprint('auth', __name__)

@blueprint.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@blueprint.route('/login', methods=['POST'])
def login_post():
    if 'username' not in request.form:
        return ''

    user = User.filter_by(username=request.form['username']).pop()

    if not user:
        flash('Invalid credentials', 'error')
        return redirect(url_for('auth.login'))

    if not user.fields.password.compare(request.form['password']):
        flash('Invalid credentials', 'error')
        return redirect(url_for('auth.login'))

    session['user_id'] = user.instance.variant_id

    return redirect(url_for('dashboard'))

@blueprint.route('/logout')
def logout():
    session.pop('user_id', None)

    return redirect(url_for('auth.login'))
