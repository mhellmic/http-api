from __future__ import with_statement

import base64
import os
import re
import tempfile

#from mock import patch
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

#    def test_requestsdb_empty_html(self):
#        with patch('eudat_http_api.auth.check_auth', return_value=True):
#            rv = self.open_with_auth('/request/', 'GET',
#                                     'testname', 'testpass')
#
#            assert rv.status_code == 200
#            # make sure that the requests list is empty
#            #assert re.search('<ul>\s*</ul>', rv.data) is not None

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
    ContainerType = 'dir'
    FileType = 'file'

    def setup(self):
        app = create_app(__name__)
        self.client = app.test_client()

    def assert_html_response(self, rv):
        assert rv.content_type.startswith('text/html')
        assert rv.mimetype == 'text/html'

    def url_list(self):
        l = [
            ('/', self.ContainerType, {
                'children': 3,
            }, True, True),
            ('/tmp/testfile', self.FileType, {
                'size': 3,
                'content': 'abc',
            }, True, True),
            ('/tmp/testfolder', self.ContainerType, {
                'children': 1,
            }, True, True),
            ('/tmp/testfolder/', self.ContainerType, {}, True, True),
            ('/tmp/testfolder/testfile', self.FileType, {
                'size': 26,
                'content': 'abcdefghijklmnopqrstuvwxyz',
            }, True, True),
            ('/tmp/emptyfolder', self.ContainerType, {
                'children': 0,
            }, True, True),
            ('/tmp/nonfolder', self.ContainerType, {}, False, True),
            ('/tmp/testfolder/nonfolder', self.ContainerType, {}, False, True),
            ('/tmp/newfolder/newfile', self.ContainerType, {}, False, False),
            ('/nonofile', self.FileType, {
                'size': 10,
                'content': '1234567890',
            }, False, True),
            ('/wrongfilesizefile', self.FileType, {
                'size': 4444,
                'content': '1234567890',
            }, False, True),
        ]
        print 'Testing %d different URLs' % len(l)
        return l

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

    def check_html(self, check_func):
        for url, objtype, objinfo, exists, parent_exists in self.url_list():
            yield (check_func, url, objtype,
                   objinfo, exists, parent_exists)

    def test_html_get(self):
        for t in self.check_html(self.check_html_get):
            yield t

    def test_html_put(self):
        for t in self.check_html(self.check_html_put):
            yield t

    def test_html_del(self):
        for t in self.check_html(self.check_html_del):
            yield t

    def check_html_get(self, url, objtype, objinfo, exists, *args):
        if objtype == self.ContainerType and exists:
            self.check_html_folder_get(url, objinfo)
        elif objtype == self.ContainerType and not exists:
            self.check_html_folder_get_404(url, objinfo)
        elif objtype == self.FileType and exists:
            self.check_html_file_get(url, objinfo)
        elif objtype == self.FileType and not exists:
            self.check_html_file_get_404(url, objinfo)

    def check_html_put(self, url, objtype, *args):
        if objtype == self.ContainerType:
            self.check_html_folder_put(url, *args)
        elif objtype == self.FileType:
            self.check_html_file_put(url, *args)

    def check_html_del(self, url, objtype, objinfo, exists, *args):
        if objtype == self.FileType:
            self.check_html_file_del(url, objinfo, exists, *args)
        elif objtype == self.ContainerType and exists:
            self.check_html_folder_del(url, objinfo, exists, *args)
        elif objtype == self.ContainerType and not exists:
            self.check_html_folder_del_404(url, objinfo, exists, *args)

    def check_html_folder_get(self, url, objinfo):
        if url[-1] != '/':
            rv = self.open_with_auth(url, 'GET',
                                     'testname', 'testpass')

            assert rv.status_code == 302
            assert rv.headers.get('Location') == 'http://localhost%s/' % url
            self.assert_html_response(rv)
        else:
            rv = self.open_with_auth(url, 'GET',
                                     'testname', 'testpass')

            assert rv.status_code == 200
            self.assert_html_response(rv)
            # check that there is a list with only list items
            assert re.search('<ul>\s*(<li>.*</li>\s*)*</ul>',
                             rv.data, re.DOTALL) is not None
            # check that there are at least two items ('.' and '..')
            assert re.search(
                '<ul>\s*<li>.*\..*</li>\s*<li>.*\.\..*</li>.*</ul>',
                rv.data, re.DOTALL) is not None

    def check_html_folder_get_404(self, url, objinfo):
        rv = self.open_with_auth(url, 'GET',
                                 'testname', 'testpass')

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_get(self, url, fileinfo):
        rv = self.open_with_auth(url, 'GET',
                                 'testname', 'testpass')

        assert rv.status_code == 200
        self.assert_html_response(rv)

        assert rv.content_length == fileinfo['size']
        assert rv.data == fileinfo['content']

    def check_html_file_get_404(self, url, fileinfo):
        rv = self.open_with_auth(url, 'GET',
                                 'testname', 'testpass')

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_del(self, url, fileinfo, exists, parent_exists):
        rv = self.open_with_auth(url, 'DELETE',
                                 'testname', 'testpass')

        if exists:
            assert rv.status_code == 204
        else:
            assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_folder_del(self, url, dirinfo, exists, parent_exists):
        if url[-1] != '/':
            rv = self.open_with_auth(url, 'DELETE',
                                     'testname', 'testpass')
            assert (rv.headers.get('Location') ==
                    'http://localhost%s/' % url)
            self.assert_html_response(rv)
        else:
            rv = self.open_with_auth(url, 'DELETE',
                                     'testname', 'testpass')

            assert rv.status_code == 204
            self.assert_html_response(rv)

    def check_html_folder_del_404(self, url, dirinfo, exists, parent_exists):
        rv = self.open_with_auth(url, 'DELETE',
                                 'testname', 'testpass')

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_put(self, url, fileinfo, exists, parent_exists):
        rv = self.open_with_auth(url, 'PUT',
                                 'testname', 'testpass',
                                 data=fileinfo['content'])

        if exists:
            assert rv.status_code == 409
        elif not parent_exists:
            assert rv.status_code == 404
        else:
            assert rv.status_code == 201
        self.assert_html_response(rv)

    def check_html_folder_put(self, url, dirinfo, exists, parent_exists):
        rv = self.open_with_auth(url, 'PUT',
                                 'testname', 'testpass')

        if exists:
            assert rv.status_code == 409
        elif not parent_exists:
            assert rv.status_code == 404
        else:
            assert rv.status_code == 201
        self.assert_html_response(rv)
