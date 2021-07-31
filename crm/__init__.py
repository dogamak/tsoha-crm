from flask import Flask, render_template, session, redirect, request, url_for, flash
import toml

import crm.settings
import crm.auth
import crm.db
from crm.models import Account, Resource

def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_file('config.toml', load=toml.load)
    # app.config.from_envvar('CRM_CONFIG', load=toml.load)

    db.init_app(app)

    @app.route('/ping')
    def healthcheck():
        return 'Pong!'

    @app.route('/')
    @auth.require_auth
    def dashboard():
        return render_template('dashboard.html', accounts=Account.all())

    @app.route('/view/<id>')
    def view_resource(id):
        from crm.models import Resource
        resource = Resource.get_resource(id)
        return render_template('view-resource.html', resource=resource)

    @app.route('/edit/<id>')
    def edit_resource(id):
        from crm.models import Resource
        resource = Resource.get_resource(id)
        return render_template('edit-resource.html', resource=resource)

    @app.route('/edit/<id>', methods=['POST'])
    def edit_resource_post(id):
        from crm.models import Resource
        resource = Resource.get_resource(id)

        if resource is None:
            return redirect(url_for('not_found'))

        for field in resource.fields:
            if field.name not in request.form:
                continue

            new_value = request.form[field.name]

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

        return render_template('create-resource.html', type=type, resource=default_values)

    @app.route('/create/<type>', methods=['POST'])
    def create_resource_post(type):
        resource = Resource.get_type(type)()

        for field in resource.fields:
            if field.name not in request.form:
                continue

            new_value = request.form[field.name]

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


    @app.context_processor
    def inject_utils():
        return dict(has_role=auth.has_role)

    app.register_blueprint(auth.blueprint)
    app.register_blueprint(settings.blueprint)

    return app
