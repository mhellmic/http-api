import os
import unittest
from eudat_http_api import app
from eudat_http_api import localstorage


class LocalStorageTest(unittest.TestCase):
    BASE_PATH = '/tmp'

    def setUp(self):
        app.config['BASE_PATH'] = LocalStorageTest.BASE_PATH

    #     we want to use local storage, but only directly?

    def test_pathsant(self):
        paths = dict()
        paths['../../etc'] = LocalStorageTest.BASE_PATH
        paths['a/b/c'] = os.path.join(LocalStorageTest.BASE_PATH, 'a/b/c')

        for test, result in paths.items():
            print 'Testing %s expected result %s' % (test, result)
            print 'Result is %s ' % localstorage.sanitize_path(test)
            assert localstorage.sanitize_path(test) == result


if __name__ == '__main__':
    unittest.main()