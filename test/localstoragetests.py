import os
from eudat_http_api import create_app

BASE_PATH = '/tmp/'
STORAGE = 'local'
DEBUG = False
TESTING = True


class TestLocalStorage:

    def setup(self):
        app = create_app(__name__)
        self.app = app

        with self.app.app_context():
            try:
                from eudat_http_api.http_storage import localstorage
                localstorage.rmdir('/foo')
            except OSError:
                pass

        self.client = app.test_client()

    def teardown(self):
        with self.app.app_context():
            try:
                from eudat_http_api.http_storage import localstorage
                localstorage.rmdir('/foo')
            except OSError:
                pass

    def test_pathsant(self):
        with self.app.app_context():
            from eudat_http_api.http_storage import localstorage

            paths = dict()
            paths['../../etc'] = BASE_PATH
            paths['a/b/c'] = os.path.join(BASE_PATH, 'a/b/c')
            paths['/foo'] = os.path.join(BASE_PATH, 'foo')

            for test, result in paths.items():
                print 'Testing %s expected result %s' % (test, result)
                print 'Result is %s ' % localstorage.sanitize_path(test)
                assert localstorage.sanitize_path(test) == result

    def test_mkdir(self):
        with self.app.app_context():
            from eudat_http_api.http_storage import localstorage

            orglist = localstorage.ls('/')
            fooExist = [i for i in orglist if i.name == 'foo']
            localstorage.mkdir('/foo')
            listing = localstorage.ls('/')
            assert len(listing) == len(orglist) + 1
            fooExist = [i for i in listing if i.name == 'foo']
            assert len(fooExist) == 1

            localstorage.rmdir('/foo')

    def test_stat(self):
        with self.app.app_context():
            from eudat_http_api.http_storage import localstorage

            res = localstorage.stat('/')
            assert 'ID' in res
