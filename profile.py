import sys
from werkzeug.contrib.profiler import ProfilerMiddleware, MergeStream
from eudat_http_api import create_app

app = create_app('config')
app.config['PROFILE'] = True
f = open('profiler.log', 'w')
stream = MergeStream(sys.stdout, f)
app.wsgi_app = ProfilerMiddleware(app.wsgi_app, stream)
app.run(debug=True, host=app.config['HOST'], port=app.config['PORT'])
