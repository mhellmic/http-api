
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import os

from flask import g
from flask import request

from irods import *


START = 'file-start'
END = 'file-end'


class StorageException(Exception):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)


class InternalException(StorageException):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)


class NotFoundException(StorageException):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)


class NotAuthorizedException(StorageException):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)


class ConflictException(StorageException):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)


def get_storage():
  """Retrieve a storage connection.

  It fetches one that has been previously
  stored during authentication, else use
  auth info from the request to create one.
  """
  conn = getattr(g, 'storageconn', None)
  if conn is None:
    auth = request.authorization
    try:
      if authenticate(auth.username, auth.password):
        conn = getattr(g, 'storageconn', None)
    except InternalException:
      g.storageconn = None

  return conn


def authenticate(username, password):
  """Authenticate with username, password.

  Returns True or False.
  Validates an existing connection.
  """
  err, rodsEnv = getRodsEnv()
  rodsEnv.rodsUserName = username

  conn, err = rcConnect(rodsEnv.rodsHost,
                        rodsEnv.rodsPort,
                        rodsEnv.rodsUserName,
                        rodsEnv.rodsZone
                        )

  if err.status != 0:
    raise InternalException('Connecting to iRODS failed: %s'
                            % (__getErrorName(err.status)))

  err = clientLoginWithPassword(conn, password)
  if err == 0:
    g.storageconn = conn
    return True
  else:
    return False


def read(path, ordered_range_list=[]):
  """Read a file from the backend storage.

  Returns a bytestream.
  In the case of one range, the bytestream is only
  the specified range.
  In case of multiple ranges, the bytestream is all
  ranges concatenated.
  If a range exceeds the size of the object, the
  bytestream goes until the object end.
  """
  conn = get_storage()

  if conn is None:
    return None

  file_handle = irodsOpen(conn, path, 'r')
  if not file_handle:
    raise NotFoundException('Path does not exist or is not a file: %s'
                            % (path))

  def stream_generator(file_handle, ordered_range_list, buffer_size=4194304):
    """Generate the bytestream.

    Default chunking is 4 MByte.

    Supports multirange request.
    (even unordened and if the ranges overlap)

    In case of no range requests, the whole file is read.

    With range requests, we seek the range, and then deliver
    the bytestream in buffer_size chunks. To stop at the end
    of the range, the make the last buffer smaller.
    This might become a performance issue, as we can have very
    small chunks. Also we deliver differently sized chunks to
    the frontend, and I'm not sure how they take it.

    The special values START and END represent the start and end
    of the file to allow for range requests that only specify
    one the two.
    """
    if not ordered_range_list:
      while True:
        data = file_handle.read(buffSize=buffer_size)
        if data == '':
          break
        yield data
    else:
      for start, end in ordered_range_list:
        if start == START:
          start = 0

        if end == END:
          file_handle.seek(start)
          while True:
            data = file_handle.read(buffSize=buffer_size)
            if data == '':
              break
            yield data

        range_size = end - start
        range_size_acc = 0
        range_buffer_size = buffer_size
        file_handle.seek(start)

        while range_size_acc < range_size:
          if (range_size - range_size_acc) < range_buffer_size:
            range_buffer_size = (range_size - range_size_acc)
          data = file_handle.read(buffSize=range_buffer_size)
          if data == '':
            break
          yield data
          range_size_acc += range_buffer_size

  gen = stream_generator(file_handle, ordered_range_list)

  return gen


def ls(path):
  """Return a generator of a directory listing."""
  conn = get_storage()

  if conn is None:
    return None

  coll = irodsCollection(conn)
  coll.openCollection(path)
  # .getId return -1 if the target does not exist or is not
  # a proper collection (e.g. a file)
  if coll.getId() < 0:
    raise NotFoundException('Path does not exist or is not a directory: %s'
                            % (coll.getCollName()))

  # TODO: remove this if it turns out that we don't need it!
  # test if the path actually points to a dir by trying
  # to open it as file. The funtion only returns a file handle
  # if it's a file, None otherwise.
  f = irodsOpen(conn, path, 'r')
  if f:
    f.close()
    raise NotFoundException('Target is not a directory: %s'
                            % (coll.getCollName()))

  def list_generator(collection):
    for sub in collection.getSubCollections():
      yield sub
    for obj in collection.getObjects():
      yield obj

  gen = list_generator(coll)

  return gen


def write(path, stream):
  pass


def mkdir(path):
  """Create a directory."""
  conn = get_storage()

  if conn is None:
    return None

  dirname, basename = os.path.split(path)
  coll = irodsCollection(conn)
  coll.openCollection(dirname)
  # see ls()
  if coll.getId() < 0:
    raise NotFoundException('Path does not exist or is not a directory: %s'
                            % (coll.getCollName()))

  err = coll.createCollection(basename)
  if err != 0:
    if err == CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
      raise ConflictException('Target already exists: %s'
                              % (path))
    elif err == CAT_INSUFFICIENT_PRIVILEGE_LEVEL:
      raise NotAuthorizedException('Target creation not allowed: %s'
                                   % (path))

  return True, ''


#### Not part of the interface anymore


def __getErrorName(code):
  return rodsErrorName(code)[0]
