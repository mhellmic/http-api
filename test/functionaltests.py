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

  def tearDown(self):

    os.close(self.db_fd)
    os.unlink(app.config['DB_NAME'])

  def __create_container(self, path):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')

      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-container", "Content-Type": "application/cdmi-container"}
      body = {}
      body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
      conn.request('PUT', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + path), json.dumps(body, indent=2), headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 201, "Create container failed")
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
      self.assertEqual(res.status, 201, "Create file failed")
      conn.close()

  def __read_container(self, path):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "*/*"}
      conn.request('GET', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + path), None, headers)      
      res = conn.getresponse()
      self.assertEqual(res.status, 200, "Read container failed")
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

  def __read_file(self, path):
      base64string = base64.encodestring('%s:%s' % (app.config['USERNAME'], app.config['PASSWORD'])).replace('\n', '')
      
      conn = httplib.HTTPConnection(app.config['HOST'],app.config['PORT'])
      headers = {"Authorization": "Basic %s" % base64string, "X-CDMI-Specification-Version": "1.0.1", "Accept": "application/cdmi-object"}
      conn.request('GET', ('/' + app.config['RODSZONE']+ '/home/' + app.config['USERNAME'] + path), None, headers)
      res = conn.getresponse()
      self.assertEqual(res.status, 200, "Read file failed")
      data = res.read()
      try:
         body = json.loads(data)
      except Exception as parsing_error:
         raise parsing_error
      self.assertIsNotNone(body['parentURI'], 'Not parentURI found which is required.')
      self.assertIsNotNone(body['objectName'], 'Not objectName found which is required.')
      self.assertIsNotNone(body['objectType'], 'Not objectType found which is required.')
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


  def test_create_read_delete_container(self):
     self.__create_container(self, 'test_container')
     self.__read_container(self, 'test_container')
     self.__delete_object(self, 'test_container')

  def test_create_read_delete_file(self):
     self.__create_file(self, 'test_file')
     self.__read_file(self, 'test_file')
     self.__delete_object(self, 'test_file')

if __name__ == '__main__':
  logging.basicConfig( stream=sys.stderr )
  logging.getLogger( "HTTPTests" ).setLevel( logging.DEBUG )
  unittest.main()
