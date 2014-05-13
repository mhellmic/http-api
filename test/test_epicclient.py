import unittest
import uuid
from httmock import all_requests, response, HTTMock
import requests
from requests.auth import HTTPBasicAuth

from eudat_http_api.epicclient import EpicClient, create_uri, HandleRecord, \
    extract_prefix_suffix

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
        self.record = HandleRecord.get_handle_with_values(
            'irods://tempZone/home/foo/bar',
            checksum=667)

        handles[create_uri(base_uri='', prefix=self.prefix,
                           suffix=self.suffix)] = \
            self.record.as_epic_json_array()

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

    def test_retrieve(self):
        with HTTMock(my_mock):
            handle = self.epic_client.retrieve_handle(
                prefix=self.prefix,
                suffix=self.suffix)
            assert handle is not None

            print handle
            assert handle.get_url_value() == 'irods://tempZone/home/foo/bar'
            assert handle.get_checksum_value() == 667

    def test_retrieve_none_existing(self):
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
                                                 handle_record=self.record)
            assert handle is None

    def test_create(self):
        with HTTMock(my_mock):
            h = HandleRecord.get_handle_with_values('http://foo.bar/', 667)
            handle = self.epic_client.create_new(prefix='666', handle_record=h)

            assert handle is not None
            assert handle.count('666') > 0
            prefix, suffix = extract_prefix_suffix(handle)
            print prefix, suffix
            handle_r = self.epic_client.retrieve_handle(prefix=prefix,
                                                        suffix=suffix)
            assert handle_r is not None
            print handle_r

            assert handle_r.get_url_value() == 'http://foo.bar/'
            assert handle_r.get_checksum_value() == 667

    def test_extract_prefix_suffix(self):
        url = 'https://epic.sara.nl/v2/handles/11096/01ea78d6-3ca8-11e3-8dbd-00163ef6845e'
        prefix, suffix = extract_prefix_suffix(url)
        assert prefix == '11096'
        assert suffix == '01ea78d6-3ca8-11e3-8dbd-00163ef6845e'


if __name__ == '__main__':
    unittest.main()





