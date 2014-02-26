from __future__ import with_statement

import base64
import os
import unittest
import re
import tempfile
import logging
import httplib
import json
import sys

from mock import patch
from eudat_http_api import app
from eudat_http_api import requestsdb

class HttpApiTestCase(unittest.TestCase):

  def setUp(self):
    self.db_fd, app.config['DB_NAME'] = tempfile.mkstemp()
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    self.app = app.test_client()
    requestsdb.init_db()
    self.__create_container('/test_container_read')
    self.__create_container('/test_container_delete') 
 
    self.__create_file('/test_container_delete/file') 
    self.__create_file('/test_container_read/file') 
    self.__create_file('/test_file_read') 
    self.__create_file('/test_file_delete') 

  def tearDown(self):
    self.__delete_object('/test_container_read')
#    self.__delete_object('/test_container_delete')
    self.__delete_object('/test_container_create')
    self.__delete_object('/test_file_create')
    self.__delete_object('/test_file_read')
#   self.__delete_object('/test_file_delete')

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

  def __create_container(self, path):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')

      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-container", "Content-Type": "application/cdmi-container"}
      body = {}
      body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
      conn.request('PUT', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + path), json.dumps(body, indent=2), headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 201, "Create init container failed")
      conn.close()

  def __create_file(self, path):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')

      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-object", "Content-Type": "application/cdmi-object"}
      body = {}
      body['mimetype'] = 'text/plain'
      body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
      body['value'] = 'test file body'
      conn.request('PUT', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + path), json.dumps(body, indent=2), headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 201, "Create init file failed")
      conn.close()

  def __delete_object(self, path):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')

      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string}
      conn.request('DELETE', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + path), None, headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 204, "Delete tear down object failed")
      conn.close()

  def test_read_storage_provider_capabilities(self):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-capability"}
      conn.request('GET', '/cdmi_capabilities/', None, headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 200, "Storage provider capabilities read failed")
      conn.close()

  def test_create_container(self):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-container", "Content-Type": "application/cdmi-container"}
      body = {}
      body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
      conn.request('PUT', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + '/test_container_create'), json.dumps(body, indent=2), headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 201, "Create container failed")
      conn.close()

  def test_read_container(self):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "*/*"}
      conn.request('GET', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + '/test_container_read'), None, headers)      
      res = conn.getresponse()
      self.assertEqual(res.status, 200, "Account read failed")
      data = res.read()
      try:
          body = json.loads(data)
      except Exception as parsing_error:
          raise parsing_error
      conn.close()
      self.assertIsNotNone(body['capabilitiesURI'], 'No capabilitiesURI found which is required.')
      self.assertIsNotNone(body['parentURI'], 'No parentURI found which is required.')
      self.assertIsNotNone(body['objectName'], 'No objectName found which is required.')
      self.assertIsNotNone(body['metadata'], 'No metadata found which is required.')
      self.assertIsNot(body['objectType'], 'application/cdmi-container', 'objectType must be application/cdmi-container')

  def test_create_file(self):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-object", "Content-Type": "application/cdmi-object"}
      body = {}
      body['mimetype'] = 'text/plain'
      body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
      body['value'] = 'test file body'
      conn.request('PUT', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + '/test_file_create'), json.dumps(body, indent=2), headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 201, "Create file failed")
      conn.close()

  def test_get_file(self):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-object"}
      conn.request('GET', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + '/test_file_read'), None, headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 200, "READ file failed")
      data = res.read()
      try:
         body = json.loads(data)
      except Exception as parsing_error:
         raise parsing_error
      self.assertIsNotNone(body['parentURI'], 'Not parentURI found which is required.')
      self.assertIsNotNone(body['objectName'], 'Not objectName found which is required.')
      self.assertIsNotNone(body['objectType'], 'Not objectType found which is required.')
      conn.close()

  def test_delete_file(self):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string}
      conn.request('DELETE', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + '/test_file_delete'), None, headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 204, "Delete file failed")
      conn.close()

  def test_delete_container(self):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string}
      conn.request('DELETE', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + '/test_container_delete'), None, headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 204, "Delete container failed")
      conn.close()

if __name__ == '__main__':
  logging.basicConfig( stream=sys.stderr )
  logging.getLogger( "HTTPTests" ).setLevel( logging.DEBUG )
  unittest.main()
