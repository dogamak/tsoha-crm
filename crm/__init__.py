from flask import Flask, render_template, session, redirect
import toml

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

    app.register_blueprint(auth.blueprint)

    return app
