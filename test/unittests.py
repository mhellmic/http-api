from __future__ import with_statement

import base64
import os
import re
import tempfile

from mock import patch
from eudat_http_api import create_app

db_fd, db_filename = tempfile.mkstemp()
SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', db_filename)
STORAGE = 'mock'
DEBUG = True
TESTING = True


class TestHttpRegisterApi:

    def setup(self):
        app = create_app(__name__)
        with app.app_context():
            from eudat_http_api.registration.models import db
            db.create_all()

        self.client = app.test_client()

    def teardown(self):
        os.close(db_fd)
        os.unlink(db_filename)

    # from https://gist.github.com/jarus/1160696
    def open_with_auth(self, url, method, username, password, data=None):
        headers = {
            'Authorization': 'Basic '
            + base64.b64encode(
                username + ":" + password)
        }
        if data:
            return self.client.open(url, method=method,
                                    headers=headers, data=data)
        else:
            return self.client.open(url, method=method,
                                    headers=headers)

    def test_requestsdb_empty_html(self):
        with patch('eudat_http_api.auth.check_auth', return_value=True):
            rv = self.open_with_auth('/request/', 'GET',
                                     'testname', 'testpass')

            assert rv.status_code == 200
            # make sure that the requests list is empty
            #assert re.search('<ul>\s*</ul>', rv.data) is not None

    # the mocking does not work with thread dispatching of the
    # registration worker. Disable this test as we most likely
    # switch to another solution eventually
    #def test_requestsdb_post_html(self):
    #    src_url = 'http://test.eudat.eu/file.txt'
    #    with patch('eudat_http_api.auth.check_auth', return_value=True), \
    #            patch('eudat_http_api.registration.registration_worker.' +
    #                  'register_data_object'):
    #        rv = self.open_with_auth('/request/', 'POST',
    #                                 'mhellmic',
    #                                 'test',
    #                                 data={'src_url': src_url})

    #        assert rv.status_code == 201
    #        assert re.search(r'<a href="request/(.*)">.*\1.*</a>',
    #                         rv.data) is not None


class TestHttpStorageApi:

    def setup(self):
        app = create_app(__name__)
        self.client = app.test_client()

    # from https://gist.github.com/jarus/1160696
    def open_with_auth(self, url, method, username, password, data=None):
        headers = {
            'Authorization': 'Basic '
            + base64.b64encode(
                username + ":" + password)
        }
        if data:
            return self.client.open(url, method=method,
                                    headers=headers, data=data)
        else:
            return self.client.open(url, method=method,
                                    headers=headers)

    def test_html_folder_get(self):
        rv = self.open_with_auth('/', 'GET',
                                 'testname', 'testpass')

        assert rv.status_code == 200
        # check that there is a list with only list items
        assert re.search('<ul>\s*(<li>.*</li>\s*)*</ul>',
                         rv.data, re.DOTALL) is not None
        # check that there are at least two items ('.' and '..')
        assert re.search(
            '<ul>\s*<li>.*\..*</li>\s*<li>.*\.\..*</li>.*</ul>',
            rv.data, re.DOTALL) is not None

    def test_html_folder_put(self):
        rv = self.open_with_auth('/newfolder', 'PUT',
                                 'testname', 'testpass')

        assert rv.status_code == 201

    def test_html_folder_delete(self):
        rv = self.open_with_auth('/oldfolder', 'DELETE',
                                 'testname', 'testpass')

        assert rv.status_code == 204

    def test_html_file_get(self):
        rv = self.open_with_auth('/testfile', 'GET',
                                 'testname', 'testpass')

        assert rv.status_code == 200
        assert rv.data == 'abc'

    def test_html_file_put(self):
        rv = self.open_with_auth('/newfile', 'PUT',
                                 'testname', 'testpass',
                                 data='abcdefg')

        assert rv.status_code == 201

    def test_html_file_delete(self):
        rv = self.open_with_auth('/oldfile', 'DELETE',
                                 'testname', 'testpass')

        assert rv.status_code == 204
