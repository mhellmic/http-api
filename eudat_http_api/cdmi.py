
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import re
import os

from urlparse import urljoin

from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import jsonify as flask_jsonify
from flask import stream_with_context

from eudat_http_api import app
from eudat_http_api import storage


def request_wants_cdmi_object():
  """adapted from http://flask.pocoo.org/snippets/45/"""
  best = request.accept_mimetypes \
      .best_match(['application/cdmi-object', 'text/html'])
  return best == 'application/cdmi-object' and \
      request.accept_mimetypes[best] > \
      request.accept_mimetypes['text/html']


def request_wants_json():
  """from http://flask.pocoo.org/snippets/45/"""
  best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
  return best == 'application/json' and \
      request.accept_mimetypes[best] > \
      request.accept_mimetypes['text/html']


@app.before_request
def check_cdmi():
  if request.headers.get('Content-Type').startswith('application/cdmi'):
    g.cdmi = True
    g.cdmi_version = request.headers.get('X-CDMI-Specification-Version')
  else:
    g.cdmi = False


def jsonify():
  return flask_jsonify()


def make_absolute_path(path):
  if path != '/':
    return '/%s' % path
  else:
    return '/'


def get_parent_path(path):
  return os.path.dirname(path[:-1]) + '/'


def create_dirlist_dict(dir_list, path):
  """Returns a dictionary with the directory entries."""
  def make_abs_link(name, path):
    return urljoin(path, name)

  nav_links = [storage.StorageDir('.', path),
               storage.StorageDir('..', get_parent_path(path))]

  return map(lambda x: {'name': x.name,
                        'path': x.path,
                        'metadata': storage.stat(x.path, True)},
             nav_links + dir_list)


def get_cdmi_file_obj(path):
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

  print 'range requests', range_requests
  try:
    (stream_gen,
     file_size,
     content_len,
     range_list) = storage.read(path, range_requests)
  except storage.IsDirException as e:
    return redirect('%s/' % path)
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401

  response_headers = {}
  response_headers['Content-Length'] = content_len
  # Do not try to guess the type
  #response_headers['Content-Type'] = 'application/octet-stream'

  response_status = 200
  multipart = False
  if file_size != content_len:
    response_status = 206
    if len(range_list) > 1:
      multipart = True
    else:
      response_headers['Content-Range'] = '%d-%d/%d' % (range_list[0][0],
                                                        range_list[0][1],
                                                        file_size)

  multipart_frontier = 'frontier'
  if multipart:
      del response_headers['Content-Length']
      response_headers['Content-Type'] = ('multipart/byteranges; boundary = %s'
                                          % multipart_frontier)

  def wrap_multipart_stream_gen(stream_gen, delim):
    multipart = False
    for segment_size, data in stream_gen:
      if segment_size:
        multipart = True
        app.logger.debug('started a multipart segment')
        #yield '\n--%s\n\n%s' % (delim, data)
        yield '\n--%s\nContent-Length: %d\n\n%s' % (delim, segment_size, data)
      else:
        yield data
    if multipart:
      yield '\n--%s--' % delim
      # yield 'epilogue'

  wrapped_stream_gen = wrap_multipart_stream_gen(stream_gen,
                                                 multipart_frontier)

  return Response(stream_with_context(wrapped_stream_gen),
                  headers=response_headers,
                  status=response_status)


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


def put_cdmi_file_obj(path):
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


def del_cdmi_file_obj(path):
  """Delete a file through CDMI."""

  try:
    storage.rm(path)
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
    return flask_jsonify(delete='Deleted: %s' % (path)), 204
  else:
    return 'Deleted: %s' % (path), 204


def get_cdmi_dir_obj(path):
  """Get a directory entry through CDMI.

  Get the listing of a directory.

  TODO: find a way to stream the listing.
  """

  if g.cdmi:
    pass  # parse CDMI input

  try:
    dir_list = [x for x in storage.ls(path)]
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.StorageException as e:
    return e.msg, 500

  if request_wants_cdmi_object():
    pass
  elif request_wants_json():
    return flask_jsonify(dirlist=create_dirlist_dict(dir_list, path))
  else:
    return render_template('dirlisting.html',
                           dirlist=dir_list,
                           path=path,
                           parent_path=get_parent_path(path))


def put_cdmi_dir_obj(path):
  """Put a directory entry through CDMI.

  Create a directory.
  """

  try:
    storage.mkdir(path)
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.ConflictException as e:
    return e.msg, 409
  except storage.StorageException as e:
    return e.msg, 500

  return flask_jsonify(create='Created')


def del_cdmi_dir_obj(path):
  """Delete a directory through CDMI."""

  try:
    storage.rmdir(path)
  except storage.NotFoundException as e:
    return e.msg, 404
  except storage.NotAuthorizedException as e:
    return e.msg, 401
  except storage.ConflictException as e:
    return e.msg, 409
  except storage.StorageException as e:
    return e.msg, 500

  return flask_jsonify(delete='Deleted: %s' % (path))
