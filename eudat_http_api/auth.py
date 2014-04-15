# -*- coding: utf-8 -*-

from __future__ import with_statement

from functools import wraps
from flask import abort, request, Response
from eudat_http_api.http_storage import storage


class AuthException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


def check_auth(username, password):
    """Check username and password.

  Contact the auth-service to check the
  credentials.
  """

    try:
        return storage.authenticate(username, password)
    except storage.StorageException as e:
        raise AuthException('Internal server error: %s'
                            % (e.msg))


#

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        try:
            if not auth:
                return authenticate()
            if not check_auth(auth.username, auth.password):
                abort(403)
        except AuthException as e:
            return e.msg, 500
        return f(*args, **kwargs)

    return decorated
