
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import os

from flask import g
from flask import request

from irods import *


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


def read(conn, path):
  pass


def ls(conn, path):
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


def write(conn, path, stream):
  pass


def mkdir(conn, path):
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
