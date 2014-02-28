import sys
from werkzeug.contrib.profiler import ProfilerMiddleware, MergeStream
from eudat_http_api import app

app.config['PROFILE'] = True
f = open('profiler.log', 'w')
stream = MergeStream(sys.stdout, f)
app.wsgi_app = ProfilerMiddleware(app.wsgi_app, stream)
app.run(debug = True)
