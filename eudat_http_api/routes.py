
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

from eudat_http_api import app
from eudat_http_api import requestsdb
from eudat_http_api import registration_worker
from eudat_http_api import invenioclient
from eudat_http_api import auth
from eudat_http_api import cdmi
import flask
from flask import request
from flask import json

# it seems not to be possible to send
# http requests forma separate Process
#from multiprocessing import Process
from threading import Thread

import requests


@app.route('/hello', methods=['GET'])
def get_hello():
  return 'hello'


@app.route('/google', methods=['GET'])
def get_google():
  return requests.get('http://google.com').url


@app.route('/redir', methods=['GET'])
def get_redir():
  return flask.redirect(flask.url_for('get_hello'), 302)


#### /request container ####


def request_wants_json():
  """from http://flask.pocoo.org/snippets/45/"""
  best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
  return best == 'application/json' and \
      request.accept_mimetypes[best] > \
      request.accept_mimetypes['text/html']


@app.route('/request/', methods=['GET'])
@auth.requires_auth
def get_requests():
  """Get a list of all requests."""
  requests = requestsdb.query_db('select * from requests', ())

  response_dict = {}
  for r in requests:
    response_dict[r['id']] = {
        'status': r['status_description'],
        'link': '%s%s' % (flask.request.url, r['id'])
    }

  if request_wants_json():
    return flask.jsonify(response_dict)
  else:
    return flask.render_template('requests.html', request_dict=response_dict)


def make_request_id_creator():
  import random

  def rnd():
    return str(random.random())[2:]
  return rnd


create_request_id = make_request_id_creator()


@app.route('/request/', methods=['POST'])
@auth.requires_auth
def post_request():
  """Submit a new request to register a file.

  Specify in the message body:
  src: url of the source file
  checksum: the file you expect the file will have.

  The function returns a URL to check the status of the request.
  The URL includes a request ID.
  """
  app.logger.debug('Entering post_request()')

  # get the src_url
  req_body = None
  if flask.request.headers.get('Content-Type') == 'application/json':
    req_body = json.loads(flask.request.data)
  else:
    req_body = flask.request.form

  src_url = req_body['src_url']

  # check if src is a valid URL

  # push request information to request DB
  request_id = create_request_id()

  request = requestsdb.insert_db(
      'insert into requests(id, status, status_description, src_url) \
          values (?, "W", "waiting to be started", ?)', [request_id, src_url]
  )

  # start worker
  p = Thread(target=registration_worker.register_data_object,
             args=(request_id,))
  p.start()

  if request_wants_json():
    return flask.jsonify(reques_id=request_id), 201
  else:
    return flask.render_template('requestcreated.html',
        request_id=request_id), 201


@app.route('/request/<request_id>', methods=['GET'])
@auth.requires_auth
def get_request(request_id):
  """Poll the status of a request by ID."""

  # fetch id information from DB
  request = requestsdb.query_db_single('select * from requests where id = :id',
                                       {'id': request_id})

  # return request status
  return json.dumps(request['status_description'])


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
