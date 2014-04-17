#from eudat_http_api import db
from flask.ext.sqlalchemy import SQLAlchemy
from marshmallow import Serializer, fields

db = SQLAlchemy()


class RegistrationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    src_url = db.Column(db.String(2000), nullable=False)
    status = db.Column(db.String(40))
    status_description = db.Column(db.String(2000))
    timestamp = db.Column(db.DateTime)
    checksum = db.Column(db.String(32))
    pid = db.Column(db.String(2000))

    @property
    def serialize(self):
        return {
            'id': self.id,
            'src_url': self.src_url,
            'status': 'A'
        }

    def __repr__(self):
        return "<Request id=%r stat=%r>" % (self.id, self.status_description)


class RegistrationRequestSerializer(Serializer):
    status_description = fields.Function(
        lambda obj: obj.status_description.split(';'))

    class Meta:
        fields = ('id',
                  'src_url',
                  'status',
                  'status_description',
                  'timestamp',
                  'checksum',
                  'pid')
