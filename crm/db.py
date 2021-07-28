import click
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

import crm.models

def get_db():
    return db

def close_db(e=None):
    pass

def init_db():
    db.create_all()

@click.command('db:init')
@with_appcontext
def init_db_command():
    init_db()

@click.command('db:create-admin')
@click.argument('username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_admin_command(username, password):
    db = get_db()

    from crm.models import User
    admin = User(username=username)
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    print(f'Administrator user account "{username}" created.')
    

def init_app(app):
    db.init_app(app)
    migrate.init_app(app, db)
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)
