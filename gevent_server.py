from gevent.pywsgi import WSGIServer
from eudat_http_api import create_app

app = create_app('config')

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
