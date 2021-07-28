from crm.db import db
from enum import Enum

from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(Enum):
    Administrator = 'Administrator'
    Sales = 'Sales'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    password_hash = db.Column(db.String)

    def set_password(self, new_password):
        self.password_hash = generate_password_hash(new_password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

