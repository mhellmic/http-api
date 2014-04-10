
import unittest

from eudat_http_api.epicclient import EpicClient
from eudat_http_api.epicclient import create_uri
import json


class FakedHttpClient():

    def __init__(self):
        self.handles = dict()
        self.baseuri = ''

    def get(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(baseuri=self.baseuri, prefix=prefix, suffix=suffix)
        class Response():
            pass

        r = Response()
        r.status_code = 200
        r.content = self.handles[uri]
        print 'GET %s' % uri
        return r


    def addHandle(self, suffix, prefix, value):
        self.handles[create_uri(baseuri=self.baseuri, prefix=prefix, suffix=suffix)] = value
        print self.handles





class TestCase(unittest.TestCase):

    def setUp(self):
        self.httpclient = FakedHttpClient()

        self.httpclient.addHandle(prefix='11858', suffix='00-ZZZZ-0000-0000-000C-7',
                              value='{ "handle": "11858/00-ZZZZ-0000-0000-000C-7", '
                                    '"responseCode": 1, '
                                    '"values": [ { "data": "0", "index": 2, '
                                    '"timestamp": "1970-01-01T00:00:00Z", "ttl": 86400, "type": "FILESIZE" }, '
                                        '{ "data": "GWDG", "index": 5, "timestamp": "1970-01-01T00:00:00Z", "ttl": 86400, "type": "TITLE" }, '
                                        '{ "data": "demo2", "index": 8, "timestamp": "1970-01-01T00:00:00Z", "ttl": 86400, "type": "CREATOR" }, '
                                        '{ "data": { "format": "admin", "value": { "handle": "0.NA/11858", "index": 200, "permissions": "010001110000" } }, '
                                        '"index": 100, "timestamp": "1970-01-01T00:00:00Z", "ttl": 86400, "type": "HS_ADMIN" }, '
                                        '{ "data": "http://www.gwdg.de/aktuell/index4.html", "index": 1, "timestamp": "1970-01-01T00:00:00Z", "ttl": 86400, "type": "URL" } '
                                    '] }'
        )
        self.epicclient = EpicClient(httpClient=self.httpclient, debug=True)


    def tearDown(self):
        pass

    def test_getUri(self):
        uri = create_uri(baseuri='http://foo.bar', prefix='9093')
        assert uri == 'http://foo.bar/9093'
        uri = create_uri(baseuri='http://foo.bar', prefix='9093', suffix='666')
        assert uri == 'http://foo.bar/9093/666'

    def test_retrieve(self):
        response = self.epicclient.retrieveHandle(prefix='11858', suffix='00-ZZZZ-0000-0000-000C-7')
        assert response != None
        # jj: not sure if we should return string or json?
        response = json.loads(response)
        assert response['values'][0]['type']=='FILESIZE'
        assert response['values'][1]['type']=='TITLE'





