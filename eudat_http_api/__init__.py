from flask import Flask

app = Flask(__name__)
app.config.from_object('config')

if not app.debug:
  import logging
  from SysLogHandler import SysLogHandler
  file_handler = SysLogHandler()
  file_handler.setLevel(logging.WARNING)
  app.logger.addHandler(file_handler)


from eudat_http_api import routes
from eudat_http_api.requestsdb import init_db
