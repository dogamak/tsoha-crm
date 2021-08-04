import hashlib

from flask import url_for
from sqlalchemy.sql import func
from crm.db import db

class File(db.Model):
    hash = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)

    def get_url(self):
        return url_for('serve_file', hash=self.hash, name=self.name)

    @classmethod
    def create_from(cls, file, **kwargs):
        content = file.read()
        hash = hashlib.sha256(content).hexdigest()

        return cls(hash=hash, content=content, **kwargs)
