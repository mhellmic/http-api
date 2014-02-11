
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import base64
import os
import unittest
import re
import tempfile

from mock import patch

from eudat_http_api import app
from eudat_http_api import requestsdb


class HttpApiTestCase(unittest.TestCase):

  def setUp(self):
    self.db_fd, app.config['DB_NAME'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    self.app = app.test_client()
    requestsdb.init_db()

  def tearDown(self):
    os.close(self.db_fd)
    os.unlink(app.config['DB_NAME'])

  # from https://gist.github.com/jarus/1160696
  def open_with_auth(self, url, method, username, password, data=None):
    headers = {
        'Authorization': 'Basic '
        + base64.b64encode(
          username + ":" + password)
    }
    if data:
      return self.app.open(url, method=method, headers=headers, data=data)
    else:
      return self.app.open(url, method=method, headers=headers)

  def test_requestsdb_empty_html(self):
    with patch('eudat_http_api.auth.check_auth', return_value=True), \
        patch('eudat_http_api.registration_worker.register_data_object'):
          rv = self.open_with_auth('/request/', 'GET',
                                   'mhellmic',
                                   'test')

    assert rv.status_code == 200
    # make sure that the requests list is empty
    assert re.search('<ul>\s*</ul>', rv.data) is not None

  def test_requestsdb_post_html(self):
    src_url = 'http://test.eudat.eu/file.txt'
    with patch('eudat_http_api.auth.check_auth', return_value=True), \
        patch('eudat_http_api.registration_worker.register_data_object'):
          rv = self.open_with_auth('/request/', 'POST',
                                   'mhellmic',
                                   'test',
                                   data={'src_url': src_url})

    assert rv.status_code == 201
    assert re.search(r'<a href="request/(.*)">.*\1.*</a>',
                     rv.data) is not None

if __name__ == '__main__':
  unittest.main()
