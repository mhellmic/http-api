
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Interface functions and the URLs they match.

We have to be careful with the order of the function.
Flask lets you specify URLs with trailing slashes and
redirects the client, if she types the URL without the
slash. In the namespace, however, we have constructs
for files and directories whose only difference is the
trailing slash.
If the URLs without trailing slash are after the ones
with in the source code, then the one with trailing
slash matches and flask autocompletes.

Thus write:
  @app.route('/home/<file>')
  @app.route('/home/<dir>/')
and not:
  @app.route('/home/<dir>/')
  @app.route('/home/<file>')

Subtle, but vicious.
"""

from __future__ import with_statement
from datetime import datetime

from eudat_http_api import app, db
from eudat_http_api import requestsdb
from eudat_http_api import registration_worker
from eudat_http_api import invenioclient
from eudat_http_api import auth
from eudat_http_api import cdmi
from models import RegistrationRequest, RegistrationRequestSerializer
import flask
from flask import request
from flask import json
from flask import redirect, abort
from config import REQUESTS_PER_PAGE

# it seems not to be possible to send
# http requests from a separate Process
#from multiprocessing import Process
from threading import Thread

import requests



def request_wants_json():
  """from http://flask.pocoo.org/snippets/45/"""
  best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
  return best == 'application/json' and \
      request.accept_mimetypes[best] > \
      request.accept_mimetypes['text/html']


@app.route('/request/', methods=['GET'])
@auth.requires_auth
def get_requests():
  """Get a requests list."""

  page = int(request.args.get('page', '1'))

  requests = RegistrationRequest.query.order_by(RegistrationRequest.timestamp.desc()).paginate(page, REQUESTS_PER_PAGE, False)

  #TODO: pagination in json?
  if request_wants_json():
      return flask.jsonify({"requests": RegistrationRequestSerializer(requests.items, many=True).data})

  return flask.render_template('requests.html', requests=requests)


@app.route('/request/', methods=['POST'])
@auth.requires_auth
def post_request():
  """Submit a new registration request

  Specify in the message body:
  src: url of the source file
  checksum: the file you expect the file will have.

  The function returns a URL to check the status of the request.
  The URL includes a request ID.
  """
  app.logger.debug('Entering post_request()')

  req_body = None
  if flask.request.headers.get('Content-Type') == 'application/json':
    req_body = json.loads(flask.request.data)
  else:
    req_body = flask.request.form

  src_url = req_body['src_url']
  #TODO: check if src is a valid URL
  r = RegistrationRequest(src_url=src_url, status_description='W', timestamp=datetime.utcnow())
  db.session.add(r)
  db.session.commit()

  # start worker
  p=Thread(target=registration_worker.register_data_object,
             args=(r.id))
  p.start()

  if request_wants_json():
    return flask.jsonify(request_id=r.id), 201
  else:
    return flask.render_template('requestcreated.html',request=r), 201


@app.route('/request/<request_id>', methods=['GET'])
@auth.requires_auth
def get_request(request_id):
  """Poll the status of a request by ID."""
  r = RegistrationRequest.query.get(request_id)

  #TODO: json error?
  if r is None:
      return abort(404)

  if request_wants_json():
      return flask.jsonify({'request': RegistrationRequestSerializer(r).data})

  return flask.render_template('singleRequest.html', r=r)


#### /registered container ####


@app.route('/registered/<pid_prefix>/', methods=['GET'])
@auth.requires_auth
def get_pids_by_prefix():

  # search PIDs with this prefix on handle.net

  # return list of PIDs
  # (with links to /registered/<full_pid>) to download
  pass


@app.route('/registered/<pid_prefix>/<pid_suffix>', methods=['GET'])
@auth.requires_auth
def get_pid_by_handle(pid_prefix, pid_suffix):
  """Retrieves a data object by PID."""
  pid = pid_prefix + '/' + pid_suffix

  if 'metadata' in flask.request.args:
    invenioclient.get_metadata(pid)

  # resolve PID

  # extract link to data object

  # choose link to data object

  # return data object
  return 'nothing there, baeh!'


#### internally used CDMI requests ####


# These requests are to access files that are
# living in the supported iRODS zones


@app.route('/', methods=['GET'])
@app.route('/<path:objpath>', methods=['GET'])
@auth.requires_auth
def get_cdmi_obj(objpath='/'):
  absolute_objpath = cdmi.make_absolute_path(objpath)
  if absolute_objpath[-1] == '/':
    return cdmi.get_cdmi_dir_obj(absolute_objpath)
  else:
    return cdmi.get_cdmi_file_obj(absolute_objpath)


@app.route('/', methods=['PUT'])
@app.route('/<path:objpath>', methods=['PUT'])
@auth.requires_auth
def put_cdmi_obj(objpath):
  absolute_objpath = cdmi.make_absolute_path(objpath)
  if absolute_objpath[-1] == '/':
    return cdmi.put_cdmi_dir_obj(absolute_objpath)
  else:
    return cdmi.put_cdmi_file_obj(absolute_objpath)


@app.route('/', methods=['DELETE'])
@app.route('/<path:objpath>', methods=['DELETE'])
@auth.requires_auth
def del_cdmi_obj(objpath):
  absolute_objpath = cdmi.make_absolute_path(objpath)
  if absolute_objpath[-1] == '/':
    return cdmi.del_cdmi_dir_obj(absolute_objpath)
  else:
    return cdmi.del_cdmi_file_obj(absolute_objpath)
