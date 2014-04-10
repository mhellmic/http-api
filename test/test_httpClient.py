

import unittest

from eudat_http_api.epicclient import HttpClient
from requests.auth import HTTPBasicAuth

class TestCase(unittest.TestCase):

    def setUp(self):
        self.client = HttpClient('http://www.google.com', HTTPBasicAuth('user', 'pass'))


    def tearDown(self):
        pass

    def test_get(self):
        response = self.client.get(prefix='/', suffix='')
        assert response.status_code == 200
        #check if the credentials are included:
        assert response.request.headers['Authorization'].startswith('Basic')

    def test_get_with_custom_header(self):
        response = self.client.get(prefix='/', suffix='', headers={'X-Special': 'foo'})
        assert response.status_code == 200
        assert response.request.headers['X-Special'] == 'foo'






