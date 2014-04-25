import unittest
import uuid

from eudat_http_api.epicclient import EpicClient, convert_to_handle
from eudat_http_api.epicclient import create_uri
import json


def extract_prefix_suffix(handle, baseuri):
    myurl = handle
    myurl.replace(baseuri, '')
    array = myurl.split('/')
    return array[-2], array[-1]


class FakedHttpClient():
    def __init__(self):
        self.handles = dict()
        self.base_uri = ''

    def get(self, prefix, suffix, *args, **kwargs):
        uri = create_uri(base_uri=self.base_uri, prefix=prefix, suffix=suffix)

        class Response():
            pass

        r = Response()
        r.status_code = 200
        r.content = self.handles[uri]
        print 'GET %s' % uri
        return r

    def post(self, prefix, headers, data):
        print 'Posting to %s' % prefix
        suffix = str(uuid.uuid1())
        self.add_handle(prefix=prefix, suffix=suffix, value=data)
        class Response():
            pass

        r = Response()
        r.status_code = 201
        r.headers = {'Location': create_uri(base_uri=self.base_uri, prefix=prefix, suffix=suffix)}
        return r

    def add_handle(self, prefix, suffix, value):
        self.handles[create_uri(base_uri=self.base_uri, prefix=prefix, suffix=suffix)] = value
        print self.handles


class TestCase(unittest.TestCase):
    def setUp(self):
        self.http_client = FakedHttpClient()

        self.http_client.add_handle(prefix='11858', suffix='00-ZZZZ-0000-0000-000C-7',
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
        self.epic_client = EpicClient(http_client=self.http_client, debug=True)

    def tearDown(self):
        pass

    def test_create_uri(self):
        uri = create_uri(base_uri='http://foo.bar', prefix='9093')
        assert uri == 'http://foo.bar/9093/'
        uri = create_uri(base_uri='http://foo.bar', prefix='9093', suffix='666')
        assert uri == 'http://foo.bar/9093/666'

    def test_create_handle_wo_checksum(self):
        a = convert_to_handle('http://foo.bar/')
        assert a is not None
        json_array = json.loads(a)
        assert len(json_array) == 1
        assert json_array[0]['type'] == 'URL'
        assert json_array[0]['parsed_data'] == 'http://foo.bar/'

    def test_create_handle_w_checksum(self):
        a = convert_to_handle('http://foo.bar/', 666)
        assert a is not None
        json_array = json.loads(a)
        assert len(json_array) == 2
        assert json_array[0]['type'] == 'URL'
        assert json_array[0]['parsed_data'] == 'http://foo.bar/'

        assert json_array[1]['type'] == 'CHECKSUM'
        assert json_array[1]['parsed_data'] == 666

    def test_retrieve(self):
        response = self.epic_client.retrieve_handle(prefix='11858', suffix='00-ZZZZ-0000-0000-000C-7')
        assert response is not None
        # jj: not sure if we should return string or json?
        response = json.loads(response)
        assert response['values'][0]['type'] == 'FILESIZE'
        assert response['values'][1]['type'] == 'TITLE'

    def test_create(self):
        response = self.epic_client.create_new(prefix='666', location='http://foo.bar/', checksum=667)
        assert response is not None
        assert response.count('666') > 0
        prefix, suffix = extract_prefix_suffix(response, '')

        handle = self.epic_client.retrieve_handle(prefix=prefix, suffix=suffix)
        assert response is not None
        response = json.loads(handle)
        print response

        assert len(response) == 2
        assert response[0]['type'] == 'URL'
        assert response[0]['parsed_data'] == 'http://foo.bar/'

        assert response[1]['type'] == 'CHECKSUM'
        assert response[1]['parsed_data'] == 667









