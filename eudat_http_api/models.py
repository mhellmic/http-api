from eudat_http_api import db
from marshmallow import Serializer, fields

class RegistrationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    src_url = db.Column(db.String(2000), nullable=False)
    status_description = db.Column(db.Enum('W', 'S', 'E', 'SP', 'DP', 'C', 'P', 'FC', 'A', name='status_types'))
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
    class Meta:
        fields = ('id', 'src_url', 'status_description', 'timestamp', 'checksum', 'pid')
