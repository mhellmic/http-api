from mock import patch
import os
from eudat_http_api import create_app

# please use only one here
EXPORTEDPATHS = ['/tmp']
STORAGE = 'local'
DEBUG = False
TESTING = True


class TestLocalStorage:
    from collections import namedtuple
    Auth = namedtuple('Auth', 'username password')

    userinfo = Auth('test', 'pass')

    def setup(self):
        app = create_app(__name__)
        self.app = app

        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.localstorage._get_authentication',
                return_value=self.userinfo):
            from eudat_http_api.http_storage import localstorage
            try:
                localstorage.rmdir('/tmp/foo')
            except localstorage.NotFoundException:
                pass

        self.client = app.test_client()

    def teardown(self):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.localstorage._get_authentication',
                return_value=self.userinfo):
            from eudat_http_api.http_storage import localstorage
            try:
                localstorage.rmdir('/tmp/foo')
            except localstorage.NotFoundException:
                pass

    #def test_pathsant(self):
    #    with self.app.test_request_context(), \
    #            patch(
    #            'eudat_http_api.http_storage.localstorage._get_authentication',
    #            return_value=self.userinfo):
    #        from eudat_http_api.http_storage import localstorage

    #        paths = dict()
    #        paths['../../etc'] = BASE_PATH
    #        paths['a/b/c'] = os.path.join(BASE_PATH, 'a/b/c')
    #        paths['/foo'] = os.path.join(BASE_PATH, 'foo')

    #        for test, result in paths.items():
    #            print 'Testing %s expected result %s' % (test, result)
    #            print 'Result is %s ' % localstorage.sanitize_path(test)
    #            assert localstorage.sanitize_path(test) == result

    def test_mkdir(self):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.localstorage._get_authentication',
                return_value=self.userinfo):
            from eudat_http_api.http_storage import localstorage

            orglist = localstorage.ls('/tmp')
            fooExist = [i for i in orglist if i.name == 'foo']
            localstorage.mkdir('/tmp/foo')
            listing = localstorage.ls('/tmp')
            assert len(listing) == len(orglist) + 1
            fooExist = [i for i in listing if i.name == 'foo']
            assert len(fooExist) == 1

            localstorage.rmdir('/tmp/foo')

    def test_stat(self):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.localstorage._get_authentication',
                return_value=self.userinfo):
            from eudat_http_api.http_storage import localstorage

            res = localstorage.stat('/tmp')
            assert 'type' in res
            assert 'children' in res
