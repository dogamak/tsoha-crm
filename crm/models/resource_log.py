from crm.db import db

class ResourceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    subject = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    message = db.Column(db.String, nullable=False)

    resource = db.relationship('Resource')
    user = db.relationship('User')
