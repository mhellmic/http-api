from gevent.pywsgi import WSGIServer
from eudat_http_api import app

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
