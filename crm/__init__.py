from flask import Flask, render_template, session, redirect, request, url_for, flash
import toml

import crm.settings
import crm.auth
import crm.db

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
        return render_template('dashboard.html')

    @app.context_processor
    def inject_utils():
        return dict(has_role=auth.has_role)

    app.register_blueprint(auth.blueprint)
    app.register_blueprint(settings.blueprint)

    return app
