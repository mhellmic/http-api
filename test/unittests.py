from __future__ import with_statement

import base64
import os
import unittest
import re
import tempfile
import logging
import sys

from mock import patch
from eudat_http_api import create_app

db_fd, db_filename = tempfile.mkstemp()
SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', db_filename)
STORAGE = 'local'
DEBUG = True
TESTING = True


class HttpApiTestCase(unittest.TestCase):

    def setUp(self):
        app = create_app(__name__)
        with app.app_context():
            from eudat_http_api.registration.models import db
            db.create_all()

        self.app = app.test_client()

    def tearDown(self):
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
            return self.app.open(url, method=method,
                                 headers=headers, data=data)
        else:
            return self.app.open(url, method=method,
                                 headers=headers)

    def test_requestsdb_empty_html(self):
        with patch('eudat_http_api.auth.check_auth', return_value=True):
            rv = self.open_with_auth('/request/', 'GET',
                                     'mhellmic',
                                     'test')

            assert rv.status_code == 200
            # make sure that the requests list is empty
            print rv.data
            assert re.search('<ul>\s*</ul>', rv.data) is not None

    def test_requestsdb_post_html(self):
        src_url = 'http://test.eudat.eu/file.txt'
        with patch('eudat_http_api.auth.check_auth', return_value=True), \
                patch('eudat_http_api.registration.registration_worker.' +
                      'register_data_object'):
            rv = self.open_with_auth('/request/', 'POST',
                                     'mhellmic',
                                     'test',
                                     data={'src_url': src_url})

            assert rv.status_code == 201
            assert re.search(r'<a href="request/(.*)">.*\1.*</a>',
                             rv.data) is not None


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger("HTTPTests").setLevel(logging.DEBUG)
    unittest.main()
