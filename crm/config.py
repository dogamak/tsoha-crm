import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:tsoha@localhost/postgres'
    SECRET_KEY = 'topsecret123'

class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
    SECRET_KEY = os.environ.get('SECRET_KEY')

def get_config(app):
    if app.config['ENV'] == 'testing':
        return TestingConfig
    elif app.config['ENV'] == 'development':
        return DevelopmentConfig
    else:
        raise Exception('Environment not configured: ' + app.config['ENV'])
