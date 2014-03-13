import os
import unittest
from eudat_http_api import app
from eudat_http_api import localstorage


class LocalStorageTest(unittest.TestCase):
    BASE_PATH = '/tmp/'

    def setUp(self):
        app.config['BASE_PATH'] = LocalStorageTest.BASE_PATH
        try:
            localstorage.rmdir('/foo')
        except OSError:
            pass

    def tearDown(self):
        try:
            localstorage.rmdir('/foo')
        except OSError:
            pass

    def test_pathsant(self):
        paths = dict()
        paths['../../etc'] = LocalStorageTest.BASE_PATH
        paths['a/b/c'] = os.path.join(LocalStorageTest.BASE_PATH, 'a/b/c')
        paths['/foo'] = os.path.join(LocalStorageTest.BASE_PATH, 'foo')

        for test, result in paths.items():
            print 'Testing %s expected result %s' % (test, result)
            print 'Result is %s ' % localstorage.sanitize_path(test)
            assert localstorage.sanitize_path(test) == result


    def test_mkdir(self):
        orglist = localstorage.ls('/')
        fooExist = [i for i in orglist if i.name == 'foo']
        localstorage.mkdir('/foo')
        listing = localstorage.ls('/')
        assert len(listing) == len(orglist) + 1
        fooExist = [i for i in listing if i.name == 'foo']
        assert len(fooExist) == 1

        localstorage.rmdir('/foo')

    def test_stat(self):
        res = localstorage.stat('/')
        assert 'ID' in res


if __name__ == '__main__':
    unittest.main()