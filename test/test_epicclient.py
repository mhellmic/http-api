import unittest
import uuid
from httmock import all_requests, response, HTTMock
import requests
from requests.auth import HTTPBasicAuth

from eudat_http_api.epicclient import EpicClient, convert_to_handle, \
    create_uri
import json


def extract_prefix_suffix(handle, baseuri):
    myurl = handle
    myurl.replace(baseuri, '')
    array = myurl.split('/')
    return array[-2], array[-1]


handles = dict()


@all_requests
def my_mock(url, request):
    print '\t>>Incoming %s on %s' % (request.method, url.path)
    if request.method == 'GET':
        if handles.has_key(url.path):
            return {'status_code': requests.codes.ok,
                    'content': handles[url.path]}
        else:
            return {'status_code': requests.codes.not_found,
                    'content': ''}

    if request.method == 'POST':
        suffix = str(uuid.uuid1())
        handles[url.path + suffix] = request.body
        headers = {'content-type': 'application/json',
                   'Location': url.path + suffix}
        content = {''}
        return response(201, content, headers, None, 5, request)

    print '\t>>Unknown method!'
    return {'status_code': requests.codes.bad_request,
            'content': 'This method is not supported'}


class TestCase(unittest.TestCase):
    def setUp(self):
        self.prefix = '11858'
        self.suffix = '00-ZZZZ-0000-0000-000C-7'
        self.base_uri = 'http://www.foo.bar'
        handles[create_uri(base_uri='', prefix=self.prefix,
                           suffix=self.suffix)] = \
            convert_to_handle('irods://tempZone/home/foo/bar', checksum=667)

        self.epic_client = EpicClient(base_uri=self.base_uri,
                                      credentials=HTTPBasicAuth('user',
                                                                'pass'),
                                      debug=True)

    def tearDown(self):
        pass

    def test_create_uri(self):
        uri = create_uri(base_uri='http://foo.bar', prefix='9093')
        assert uri == 'http://foo.bar/9093/'
        uri = create_uri(base_uri='http://foo.bar',
                         prefix='9093', suffix='666')
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
        with HTTMock(my_mock):
            handle = self.epic_client.retrieve_handle(
                prefix=self.prefix,
                suffix=self.suffix)
            assert handle is not None
            # jj: not sure if we should return string or json?
            json_handle = json.loads(handle)
            print json_handle
            assert json_handle[0]['type'] == 'URL'
            assert json_handle[0][
                       'parsed_data'] == 'irods://tempZone/home/foo/bar'
            assert json_handle[1]['type'] == 'CHECKSUM'
            assert json_handle[1]['parsed_data'] == 667

    def test_retrieve_none_xisting(self):
        with HTTMock(my_mock):
            handle = self.epic_client.retrieve_handle(prefix='foo',
                                                      suffix='barr')
            assert handle is None

    def test_failed_create(self):
        @all_requests
        def failing_mock(url, request):
            return {'status_code': requests.codes.bad_request, 'content': ''}
        with HTTMock(failing_mock):
            handle = self.epic_client.create_new(prefix='666',
                                                 location='http://foo.bar/',
                                                 checksum=667)
            assert handle is None


    def test_create(self):
        with HTTMock(my_mock):
            handle = self.epic_client.create_new(prefix='666',
                                                 location='http://foo.bar/',
                                                 checksum=667)
            assert handle is not None
            assert handle.count('666') > 0
            prefix, suffix = extract_prefix_suffix(handle, self.base_uri)
            print prefix, suffix
            handle_r = self.epic_client.retrieve_handle(prefix=prefix,
                                                        suffix=suffix)
            assert handle_r is not None
            json_handle = json.loads(handle_r)
            print json_handle

            assert len(json_handle) == 2
            assert json_handle[0]['type'] == 'URL'
            assert json_handle[0]['parsed_data'] == 'http://foo.bar/'

            assert json_handle[1]['type'] == 'CHECKSUM'
            assert json_handle[1]['parsed_data'] == 667


if __name__ == '__main__':
    unittest.main()





