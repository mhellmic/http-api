from gevent.pywsgi import WSGIServer
from eudat_http_api import create_app

app = create_app('config')

ssl_args = {}

if (ssl_args['ssl_keyfile'] is not None and
        ssl_args['ssl_certfile'] is not None):
    ssl_args = {
        'ssl_keyfile': app.config.get('SSL_KEY', None),
        'ssl_certfile': app.config.get('SSL_CERT', None),
        'ca_certs': app.config.get('SSL_CACERTS', None),
    }

http_server = WSGIServer(('', 5000), app, **ssl_args)
http_server.serve_forever()
