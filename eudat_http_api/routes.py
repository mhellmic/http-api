
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

import re

from eudat_http_api import app
from eudat_http_api import requestsdb
from eudat_http_api import registration_worker
from eudat_http_api import invenioclient
from eudat_http_api import auth
from eudat_http_api import storage
from eudat_http_api import cdmi
import flask
from flask import g
from flask import request
from flask import Response
from flask import json
from flask import stream_with_context

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


def request_wants_cdmi_object():
  """adapted from http://flask.pocoo.org/snippets/45/"""
  best = request.accept_mimetypes \
      .best_match(['application/cdmi-object', 'text/html'])
  return best == 'application/cdmi-object' and \
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
      'insert into requests(id, status, status_description, src_url) \
          values (?, "W", "waiting to be started", ?)', [request_id, src_url]
  )
  print request

  # start worker
  p = Thread(target=registration_worker.register_data_object,
             args=(request_id,))
  p.start()

  return 'your thread has been started, your request id is %s' \
         % (request_id), 201


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


@app.route('/<path:dirpath>/<filename>', methods=['GET'])
@auth.requires_auth
def get_cdmi_file_obj(dirpath, filename):
  """Get a file from storage through CDMI.

  We might want to implement 3rd party copy in
  pull mode here later. That can make introduce
  problems with metadata handling, though.
  """

  def parse_range(range_str):
    start, end = range_str.split('-')
    try:
      start = int(start)
    except:
      start = storage.START

    try:
      end = int(end)
    except:
      end = storage.END

    return (start, end)

  range_requests = []
  if request.headers.get('Range'):
    ranges = request.headers.get('Range')
    range_regex = re.compile('(\d*-\d*)')
    matches = range_regex.findall(ranges)
    range_requests = map(parse_range, matches)

  try:
    stream_gen = storage.read('/%s/%s' % (dirpath, filename), range_requests)
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401

  return Response(stream_with_context(stream_gen))


class StreamWrapper(object):
  """Wrap the WSGI input so it doesn't store everything in memory.

  taken from http://librelist.com/browser//flask/2011/9/9/any-way-to-stream- \
      file-uploads/#d3f5efabeb0c20e24012605e83ce28ec

  Apparently werkzeug needs a readline method, which I added with
  the same implementation as read.
  """
  def __init__(self, stream):
    self._stream = stream

  def read(self, buffer_size):
    rv = self._stream.read(buffer_size)
    return rv

  def readline(self, buffer_size):
    rv = self._stream.read(buffer_size)
    return rv


@app.route('/<path:dirpath>/<filename>', methods=['PUT'])
@auth.requires_auth
def put_cdmi_file_obj(dirpath, filename):
  """Put a file into storage through CDMI.

  Should also copy CDMI metadata.
  Should support the CDMI put copy from a
  src URL.

  request.shallow is set to True at the beginning until after
  the wrapper has been created to make sure that nothing accesses
  the data beforehand.
  I do _not_ know the exact meaning of these things.
  """

  request.shallow = True
  request.environ['wsgi.input'] = \
      StreamWrapper(request.environ['wsgi.input'])
  request.shallow = False

  path = '/%s/%s' % (dirpath, filename)

  def stream_generator(handle, buffer_size=4194304):
    while True:
      data = handle.read(buffer_size)
      if data == '':
        break
      yield data

  gen = stream_generator(request.stream)
  bytes_written = 0
  try:
    bytes_written = storage.write(path, gen)
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.StorageException as e:
    return e.msg, 500

  return 'Created: %d' % (bytes_written), 201


@app.route('/<path:dirpath>/<filename>', methods=['DELETE'])
@auth.requires_auth
def del_cdmi_file_obj(dirpath, filename):
  """Delete a file through CDMI."""

  try:
    storage.rm('/%s/%s' % (dirpath, filename))
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.ConflictException as e:
    return e.msg, 409
  except storage.StorageException as e:
    return e.msg, 500

  if request_wants_cdmi_object():
    empty_response = Response(status=204)
    del empty_response.headers['content-type']
    return empty_response
  elif request_wants_json():
    return flask.jsonify(delete='Deleted: /%s/%s' % (dirpath, filename)), 204
  else:
    return 'Deleted: /%s/%s' % (dirpath, filename), 204


@app.route('/<path:dirpath>/', methods=['GET'])
@auth.requires_auth
def get_cdmi_dir_obj(dirpath):
  """Get a directory entry through CDMI.

  Get the listing of a directory.

  TODO: find a way to stream the listing.
  """

  if g.cdmi:
    pass  # parse CDMI input

  try:
    dir_list = [x for x in storage.ls('/%s' % (dirpath))]
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.StorageException as e:
    return e.msg, 500

  return flask.jsonify(dirlist=dir_list)


@app.route('/<path:dirpath>/<dirname>/', methods=['PUT'])
@auth.requires_auth
def put_cdmi_dir_obj(dirpath, dirname):
  """Put a directory entry through CDMI.

  Create a directory.
  """

  try:
    storage.mkdir('/%s/%s' % (dirpath, dirname))
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.ConflictException as e:
    return e.msg, 409
  except storage.StorageException as e:
    return e.msg, 500

  return flask.jsonify(create='Created')


@app.route('/<path:dirpath>/<dirname>/', methods=['DELETE'])
@auth.requires_auth
def del_cdmi_dir_obj(dirpath, dirname):
  """Delete a directory through CDMI."""

  try:
    storage.rmdir('/%s/%s' % (dirpath, dirname))
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.ConflictException as e:
    return e.msg, 409
  except storage.StorageException as e:
    return e.msg, 500

  return flask.jsonify(delete='Deleted: /%s/%s/' % (dirpath, dirname))
