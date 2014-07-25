# -*- coding: utf-8 -*-

from __future__ import with_statement


class AuthException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class AuthMethod(object):
    NoAuth, Pass, Gsi = range(3)


class Auth(object):
    """Object holding all auth/authz-relevant info.

    This object holds all relevant auth info for one request
    and can be handed through the application for further use,
    additions, or modifications.

    The method can be:
        AuthMethod.NoAuth for no authentication provided
        AuthMethod.Pass for user/password combination
        AuthMethod.Gsi for client certificate auth
    """
    method = None
    username = None
    password = None
    userdn = None
    usercert = None
    userverifiedok = None

    def __init__(self, check_auth_func):
        self.check_auth_func = check_auth_func

    def parse_request(self, request):
        """Parse all authentication info from the request.

        It checks for HTTP basic auth and client certificates,
        stores the information and sets the used method
        accordingly.
        If gsi is used, it overrides any present name/pass
        authentication used. The information is still there,
        but the auth method is set to AuthMethod.Gsi.

        This function MUST be called before is_authenticated or
        is_anonymous can be used.
        """
        auth = request.authorization
        if auth:
            self.username = auth.username
            self.password = auth.password
            self.method = AuthMethod.Pass

        self.userdn = request.headers.get('X-Client-Name', None)
        self.usercert = request.headers.get('X-Client-Cert', None)
        self.userverifiedok = request.headers.get('X-Client-Verified', None)
        if self.userdn is not None and self.userverifiedok is not None:
            self.method = AuthMethod.Gsi

    def is_authenticated(self):
        return self.check_auth_func(self)

    def is_active(self):
        return self.is_authenticated()

    def is_anonymous(self):
        return self.method == AuthMethod.NoAuth

    def __str__(self):
        print_str = 'auth method = %s, username = %s' % (self.method,
                                                         self.username)
        return print_str
