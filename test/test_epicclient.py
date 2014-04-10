
import unittest

from eudat_http_api import epicclient

class TestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_getUri(self):
        uri = epicclient.create_uri(baseuri='http://foo.bar', prefix='9093')
        assert uri == 'http://foo.bar/9093'
        uri = epicclient.create_uri(baseuri='http://foo.bar', prefix='9093', suffix='666')
        assert uri == 'http://foo.bar/9093/666'
        pass


