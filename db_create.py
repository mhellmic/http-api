from eudat_http_api.registration.models import db
from eudat_http_api import create_app

app = create_app('config')

with app.app_context():
    db.create_all()
