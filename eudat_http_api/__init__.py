from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('config')

if not app.debug:
  import logging
  from logging.handlers import SysLogHandler
  file_handler = SysLogHandler()
  file_handler.setLevel(logging.WARNING)
  app.logger.addHandler(file_handler)

db = SQLAlchemy(app)

from eudat_http_api import routes
from eudat_http_api import models
