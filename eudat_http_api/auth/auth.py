# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import current_app
from flask import Response

from flask.ext.login import LoginManager
from eudat_http_api.auth.common import AuthException
from eudat_http_api.auth.common import UserInfo
from eudat_http_api.http_storage import storage


login_manager = LoginManager()


@login_manager.unauthorized_handler
def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def check_auth(auth_info):
    """Check username and password.

  Contact the auth-service to check the
  credentials.
  """

    current_app.logger.debug('auth.check_auth with auth_info:')
    current_app.logger.debug(auth_info)
    try:
        return storage.authenticate(auth_info)
    except storage.StorageException as e:
        raise AuthException('Internal server error: %s'
                            % (e.msg))


@login_manager.request_loader
def load_user(request):
    auth_info = UserInfo(check_auth)
    auth_info.parse_request(request)
    request.auth_info = auth_info
    return auth_info
