import tempfile
import unittest
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from requests import get
from eudat_http_api.registration import registration_worker

from eudat_http_api.registration.models import RegistrationRequest
from eudat_http_api import create_app
from eudat_http_api.registration.models import db
from eudat_http_api.registration.registration_worker import check_src, \
    check_url, check_metadata, copy_data_object, get_handle, \
    stream_download, get_destination, create_storage_url, \
    get_replication_filename, \
    extract_credentials, get_checksum, get_replication_destination, \
    get_replication_command, add_task, q

from httmock import HTTMock, all_requests, response

import os


# @urlmatch(netloc=r'(.*\.)?foo.bar$')
@all_requests
def my_mock(url, request):
    return {'status_code': requests.codes.ok,
            'content': 'Incoming request %s on %s' % (request.method, url)}


@all_requests
def failing_mock(url, request):
    return {'status_code': requests.codes.not_found, 'content': ''}


class Context():
    pass


class TestCase(unittest.TestCase):
    def setUp(self):
        app = create_app('test_config')
        self.app = app
        self.client = app.test_client()
        db.create_all()

    def tearDown(self):
        db.drop_all()
        os.remove(self.app.config['DB_FILENAME'])

    def add_request(self):
        r = RegistrationRequest(src_url='http://www.foo.bar/',
                                status_description='Registration request '
                                                   'created',
                                timestamp=datetime.utcnow())
        db.session.add(r)
        db.session.commit()
        return r

    def test_check_url(self):
        c = self.prepare_context()

        with HTTMock(my_mock):
            ret = check_url(c.src_url, c.auth)

        assert ret is True

    def test_check_url_fails(self):
        c = self.prepare_context()

        with HTTMock(failing_mock):
            ret = check_url(c.src_url, c.auth)

        assert ret is False

    def test_check_src(self):
        c = self.prepare_context()
        with HTTMock(my_mock):
            ret = check_src(c)
        assert ret
        assert c.status.startswith('Checking source')
        r = RegistrationRequest.query.get(c.request_id)
        assert r.status_description.startswith('Checking source')
        assert c.status == r.status_description

    def test_check_md(self):
        c = self.prepare_context()
        with HTTMock(my_mock):
            ret = check_metadata(c)
        assert ret
        assert c.status.startswith('Checking metadata')

        r = RegistrationRequest.query.get(c.request_id)
        assert r.status_description == c.status

    def test_copy_object(self):
        return
        c = self.prepare_context()
        ret = copy_data_object(c)
        assert ret
        expected_destination = "%s/%s" % (
            registration_worker.IRODS_SAFE_STORAGE,
            '97d2ac461c3a5dd3322b2aae683994dc0bb07d2a7dd4c5198b0ed33e324a81e5')
        assert c.destination == expected_destination
        assert c.checksum == 667

    def test_get_handle(self):
        c = self.prepare_context()
        expected_location = 'http://www.foo.bar/667/111'
        c.destination = '/some/random/location'
        c.checksum = 667

        @all_requests
        def posting_mock(url, request):
            print '\t>>Incoming request %s %s' % (request.method, url.path)
            headers = {'content-type': 'application/json',
                       'Location': expected_location}
            content = {'some content'}
            return response(201, content, headers, None, 5, request)

        with HTTMock(posting_mock):
            ret = get_handle(c)

        assert ret
        assert c.pid == expected_location

    def test_start_replication(self):
        c = self.prepare_context()
        # ret = start_replication(c)
        # assert ret

    def test_stream_download(self):
        name = tempfile.mktemp()
        temp_file = open(name, 'w')
        expected_content = 20 * 'some content that we expect to be written'

        @all_requests
        def content_serving_mock(url, request):
            return {'status_code': requests.codes.ok,
                    'content': expected_content}

        with HTTMock(content_serving_mock):
            source = get('http://www.foo.bar', stream=True)
            stream_download(source, temp_file, 20)
        temp_file.close()
        assert os.path.exists(name)
        s = open(name, 'r').read()
        assert s == expected_content

    def test_create_url(self):
        c = self.prepare_context()
        c.src_url = 'foo.bar'
        destination = get_destination(c)
        url = create_storage_url(destination)
        assert url is not None
        assert url.startswith('irods://')
        assert url == 'irods://localhost:1247/tempZone/safe/' \
               '2595d08ad22c733f7a1ce713e767563e13a8dfa35baa74919c28e0f586cb424b'

    def test_replication_file_name(self):
        c = self.prepare_context()
        c.pid = 'http://localhost:5000/666/b9f71920-d4f1-11e3-81d9-f0def1d0c536'
        file_name = get_replication_filename(c)
        assert file_name == '/tempZone/replicate/b9f71920-d4f1-11e3-81d9-f0def1d0c536.replicate'

    def test_extract_credentials(self):
        username, password = extract_credentials(HTTPBasicAuth('user',
                                                               'pass'))
        assert username == 'user'
        assert password == 'pass'

    def test_get_checksum(self):
        dst = 'destination'
        checksum = get_checksum(dst)
        assert checksum == 667

    def test_get_replication_dst(self):
        c = self.prepare_context()
        expected_result = '/tempZone/replicated/97d2ac461c3a5dd3322b2aae683994dc0bb07d2a7dd4c5198b0ed33e324a81e5'
        result = get_replication_destination(c)
        assert result == expected_result

    def test_get_replication_command(self):
        c = self.prepare_context()
        c.pid = 'http://localhost:5000/666/b9f71920-d4f1-11e3-81d9-f0def1d0c536'
        c.destination = '/some/random/location'
        c.replication_destination = '/tempZone/replicated/foo.bar'
        command = get_replication_command(c)
        assert command.count(';') == 2
        pid, dst, rpl = command.split(';')
        assert pid == c.pid
        assert dst == c.destination
        assert rpl == c.replication_destination

    def test_add_task(self):
        c = self.prepare_context()
        add_task(c)
        context = q.get()
        assert c.md_url == context.md_url
        assert c.src_url == context.src_url
        assert c.request_id == context.request_id

    def prepare_context(self):
        r = self.add_request()
        c = Context()
        c.md_url = 'http://www.google.com/aaa?metadata'
        c.src_url = 'http://www.google.com/aaa?value'
        c.auth = HTTPBasicAuth('user', 'pass')
        c.request_id = r.id
        return c