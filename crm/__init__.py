from flask import Flask, render_template, session, redirect, request, url_for, flash
from sqlalchemy import select

from crm.auth import has_role, require_auth
from crm.views.auth import blueprint as auth_blueprint
from crm.views.settings import blueprint as settings_blueprint
from crm.views.resource import blueprint as resource_blueprint
import crm.db

from crm.config import get_config
from crm.models import Account, Resource, User
from crm.models.user import UserRole
from crm.models.resource import ResourceUserAssignment
from crm.access import AccessType
from crm.utils import generate_random_string

def create_app():
    app = Flask(__name__)

    app.config.from_object(get_config(app))

    crm.db.init_app(app)

    @app.route('/ping')
    def healthcheck():
        return 'Pong!'

    @app.route('/')
    @require_auth
    def dashboard():
        accounts = Account.from_statement(
            select(Account.model) \
                .join(Resource, Resource.account_id == Account.model.variant_id) \
                .join(ResourceUserAssignment, ResourceUserAssignment.resource_id == Resource.id) \
                .where(ResourceUserAssignment.user_id == session['user_id'])
                .union_all(
                    select(Account.model).where(Account.model.created_by_id == session['user_id'])
                )
        )

        return render_template('dashboard.html', accounts=accounts)

    @app.route('/create_test_account')
    def create_test_account():
        if app.config['ENV'] not in ('testing', 'development'):
            return redirect(url_for('dashboard'))

        while True:
            username = f'testing-{generate_random_string(8)}'
            user = User.filter_by(username=username)

            print(username, user)

            if len(user) == 0:
                break

        password = generate_random_string(24)
        user = User(username=username, password=password, role=UserRole.Administrator)
        user.save()
        session['user_id'] = user.instance.variant_id
        flash(f'Admin account "{user.username}" with password "{password}" created for testing purposes. You can change the username and password on the settings page.')
        return redirect(url_for('dashboard'))

    @app.route('/file/<hash>/<name>')
    def serve_file(hash, name):
        from crm.models import File
        file = File.query.get(hash)

        if file is None:
            return render_template('not_found')

        return file.content

    @app.context_processor
    def inject_utils():
        user = User.get(session['user_id']) if 'user_id' in session else None
        return dict(has_role=has_role, session_user=user, AccessType=AccessType)

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(settings_blueprint)
    app.register_blueprint(resource_blueprint)

    return app
