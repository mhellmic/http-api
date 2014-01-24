
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

from eudat_http_api import app
from eudat_http_api import requestsdb
from eudat_http_api import registration_worker
from eudat_http_api import auth
import flask
from flask import request
from flask import json

# it seems not to be possible to send
# http requests forma separate Process
#from multiprocessing import Process
from threading import Thread

import hashlib

import requests
from urlparse import urlparse

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

  print req_body

  src_url = req_body['src_url']
  print src_url

  # check if src is a valid URL

  # push request information to request DB
  request_id = create_request_id()

  request = requestsdb.insert_db(
      'insert into requests(id, status, status_description, src_url) values (?, "W", "waiting to be started", ?)', [request_id, src_url]
      )
  print request

  # start worker
  p = Thread(target=registration_worker.register_data_object, args=(request_id,))
  p.start()

  return 'your thread has been started, your request id is %s' % (request_id)

@app.route('/request/<request_id>', methods=['GET'])
@auth.requires_auth
def get_request(request_id):
  """Poll the status of a request by ID."""

  # fetch id information from DB
  request = requestsdb.query_db_single('select * from requests where id = :id', {'id': request_id})

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
def get_pid_by_handle():
  """Retrieves a data object by PID."""

  # resolve PID

  # extract link to data object

  # choose link to data object

  # return data object

  pass

#### internally used CDMI requests ####

# These requests are to access files that are
# living in the supported iRODS zones

@app.route('/<zone>/<path:filepath>', methods=['GET'])
@auth.requires_auth
def get_cdmi_irods(zone, filepath):
  """Get a file from irods storage through CDMI.

  We might want to implement 3rd party copy in
  pull mode here later. That can make introduce
  problems with metadata handling, though.
  """
  return 'you can get a file here'

@app.route('/<zone>/<path:filepath>', methods=['PUT'])
@auth.requires_auth
def put_cdmi_irods(zone, filepath):
  """Put a file into irods through CDMI.

  Should also copy CDMI metadata.
  Should support the CDMI put copy from a
  src URL.
  """
  return 'you can put a file here'

