from flask import Flask, render_template, session, redirect, request, url_for, flash
import toml

from sqlalchemy import select

import os
import crm.settings
import crm.auth
import crm.db
from crm.models import Account, Resource, User
from crm.models.resource import ResourceUserAssignment
from crm.access import AccessType

def not_found():
    return '404 - Not Found'

def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_file('config.toml', load=toml.load)

    if 'DATABASE_URL' in os.environ:
        app.config['DATABASE_URL'] = os.environ['DATABASE_URL']

    db.init_app(app)

    @app.route('/ping')
    def healthcheck():
        return 'Pong!'

    @app.route('/')
    @auth.require_auth
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

    @app.route('/view/<id>')
    def view_resource(id):
        from crm.models import Resource
        resource = Resource.get_resource(id)

        if not resource.check_access(auth.get_session_user(), AccessType.Read):
            return not_found()

        return render_template('view-resource.html', resource=resource, users=User.all())

    @app.route('/edit/<id>/assign', methods=['POST'])
    def assign_resource(id):
        from crm.models import Resource
        resource = Resource.get_resource(id)
        user = Resource.get_resource(request.form['user'])

        if not resource.check_access(auth.get_session_user(), AccessType.Write):
            return not_found()

        resource.assign_to(user)
        return redirect(url_for('view_resource', id=resource.id))

    @app.route('/edit/<resource_id>/unassign/<user_id>')
    def unassign_resource(resource_id, user_id):
        from crm.models import Resource
        resource = Resource.get_resource(resource_id)
        user = Resource.get_resource(user_id)

        if not resource.check_access(auth.get_session_user(), AccessType.Write):
            return not_found()

        resource.unassign_from(user)
        return redirect(url_for('view_resource', id=resource.id))

    @app.route('/edit/<id>')
    def edit_resource(id):
        from crm.models import Resource
        resource = Resource.get_resource(id)

        if not resource.check_access(auth.get_session_user(), AccessType.Write):
            return not_found()

        return render_template('edit-resource.html', resource=resource, AccessType=AccessType)

    @app.route('/edit/<id>', methods=['POST'])
    def edit_resource_post(id):
        from crm.models import Resource
        resource = Resource.get_resource(id)

        print(request.files, request.form)

        if resource is None:
            return redirect(url_for('not_found'))

        if not resource.check_access(auth.get_session_user(), AccessType.Write):
            return not_found()

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
                return redirect(url_for('edit_resource', id=resource.id))
        
        resource.save()

        flash('Resource updated successfully!')
        return redirect(url_for('view_resource', id=resource.id))

    @app.route('/create/<type>')
    def create_resource(type):
        resource_type = Resource.get_type(type)
        default_values = resource_type()

        if not default_values.check_access(auth.get_session_user(), AccessType.Create):
            return not_found()

        return render_template('create-resource.html', type=type, resource=default_values)

    @app.route('/create/<type>', methods=['POST'])
    def create_resource_post(type):
        resource = Resource.get_type(type)()

        if not resource.check_access(auth.get_session_user(), AccessType.Create):
            return not_found()

        user = User.get(session['user_id'])
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
                return redirect(url_for('create_resource', type=type))
        
        resource.save()

        flash('Resource created successfully!')
        return redirect(url_for('view_resource', id=resource.id))

    @app.route('/file/<hash>/<name>')
    def serve_file(hash, name):
        from crm.models import File
        file = File.query.get(hash)

        if file is None:
            return not_found()

        return file.content

    @app.context_processor
    def inject_utils():
        user = User.get(session['user_id']) if 'user_id' in session else None
        return dict(has_role=auth.has_role, session_user=user)

    app.register_blueprint(auth.blueprint)
    app.register_blueprint(settings.blueprint)

    return app
