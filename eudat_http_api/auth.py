
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

from functools import wraps

from flask import request, Response

def check_auth(username, password):
  """Check username and password.

  Contact the auth-service to check the
  credentials.

  Stub: for now it return always True
  """
  return True

def authenticate():
  """Sends a 401 response that enables basic auth"""
  return Response(
  'Could not verify your access level for that URL.\n'
  'You have to login with proper credentials', 401,
  {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
      return authenticate()
    return f(*args, **kwargs)
  return decorated
