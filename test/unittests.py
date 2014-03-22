from __future__ import with_statement

import base64
from collections import namedtuple
from itertools import product
from operator import add
import os
import re
import tempfile

from nose.tools import assert_raises

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


ContainerType = 'dir'
FileType = 'file'


class RestResource:
    ContainerType = 'dir'
    FileType = 'file'

    url = None
    path = None  # for now path and url are the same
    objtype = None
    objinfo = {}
    exists = None
    parent_exists = None

    def __init__(self, url,
                 objtype,
                 objinfo,
                 exists=True,
                 parent_exists=True):

        self.url = url
        self.objtype = objtype
        self.objinfo = objinfo
        self.exists = exists
        self.parent_exists = parent_exists
        self.path = self.url

    def is_dir(self):
        return self.objtype == self.ContainerType

    def is_file(self):
        return self.objtype == self.FileType

    def __str__(self):
        return ('url: %s; type: %s; exists: %s; parent_exists: %s'
                % (self.url,
                   self.objtype,
                   self.exists,
                   self.parent_exists)
                )

    def __repr__(self):
        return self.__str__()


def get_url_list():
    l = [
        RestResource('/', ContainerType, {
            'children': 3,
        }, True, True),
        RestResource('/tmp/testfile', FileType, {
            'size': 3,
            'content': 'abc',
        }, True, True),
        RestResource('/tmp/testfolder', ContainerType, {
            'children': 1,
        }, True, True),
        RestResource('/tmp/testfolder/', ContainerType, {
            'children': 1,
        }, True, True),
        RestResource('/tmp/testfolder/testfile', FileType, {
            'size': 26,
            'content': 'abcdefghijklmnopqrstuvwxyz',
        }, True, True),
        RestResource('/tmp/emptyfolder', ContainerType, {
            'children': 0,
        }, True, True),
        RestResource('/tmp/emptyfolder/', ContainerType, {
            'children': 0,
        }, True, True),
        RestResource('/tmp/nonfolder', ContainerType, {},
                     False, True),
        RestResource('/tmp/testfolder/nonfolder', ContainerType, {},
                     False, True),
        RestResource('/tmp/newfolder/newfile', FileType, {
            'size': 10,
            'content': '1234567890',
        }, False, False),
        RestResource('/nonofile', FileType, {
            'size': 10,
            'content': '1234567890',
        }, False, True),
        RestResource('/wrongfilesizefile', FileType, {
            'size': 4444,
            'content': '1234567890',
        }, False, True),
        RestResource('/emptyfile', FileType, {
            'size': 0,
            'content': '',
        }, False, True),
    ]
    print 'Testing %d different URLs' % len(l)
    return l


def get_user_list():
    User = namedtuple('User', 'name password valid')
    l = [
        User('testname', 'testpass', True),
        User('testname', 'notvalid', False),
        User('notvalidname', 'notvalid', False),
    ]
    print 'Testing %d different users' % len(l)
    return l


class TestHttpApi:

    def setup(self):
        app = create_app(__name__)
        self.client = app.test_client()

    def assert_html_response(self, rv):
        assert rv.content_type.startswith('text/html')
        assert rv.mimetype == 'text/html'

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
        for (resource,
             userinfo) in product(get_url_list(),
                                  get_user_list()):
            yield (check_func,
                   {
                       'url': resource.url,
                       'objtype': resource.objtype,
                       'objinfo': resource.objinfo,
                       'exists': resource.exists,
                       'parent_exists': resource.parent_exists,
                       'userinfo': userinfo
                   })

    def test_html_get(self):
        for t in self.check_html(self.check_html_get):
            yield t

    def test_html_put(self):
        for t in self.check_html(self.check_html_put):
            yield t

    def test_html_del(self):
        for t in self.check_html(self.check_html_del):
            yield t

    def check_html_get(self, params):
        if params['objtype'] == ContainerType and params['exists']:
            self.check_html_folder_get(**params)
        elif params['objtype'] == ContainerType and not params['exists']:
            self.check_html_folder_get_404(**params)
        elif params['objtype'] == FileType and params['exists']:
            self.check_html_file_get(**params)
        elif params['objtype'] == FileType and not params['exists']:
            self.check_html_file_get_404(**params)

    def check_html_put(self, params):
        if params['objtype'] == ContainerType:
            self.check_html_folder_put(**params)
        elif params['objtype'] == FileType:
            self.check_html_file_put(**params)

    def check_html_del(self, params):
        if params['objtype'] == FileType:
            self.check_html_file_del(**params)
        elif params['objtype'] == ContainerType and params['exists']:
            self.check_html_folder_del(**params)
        elif params['objtype'] == ContainerType and not params['exists']:
            self.check_html_folder_del_404(**params)

    def check_html_folder_get(self, url, objinfo, userinfo, **kwargs):
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if url[-1] != '/':
            assert rv.status_code == 302
            assert rv.headers.get('Location') == 'http://localhost%s/' % url
            self.assert_html_response(rv)
        else:
            assert rv.status_code == 200
            self.assert_html_response(rv)
            # check that there is a list with only list items
            assert re.search('<ul>\s*(<li>.*</li>\s*)*</ul>',
                             rv.data, re.DOTALL) is not None
            # check that there are at least two items ('.' and '..')
            assert re.search(
                '<ul>\s*<li>.*\..*</li>\s*<li>.*\.\..*</li>.*</ul>',
                rv.data, re.DOTALL) is not None

    def check_html_folder_get_404(self, url, objinfo, userinfo, **kwargs):
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_get(self, url, objinfo, userinfo, **kwargs):
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 200
        self.assert_html_response(rv)

        assert rv.content_length == objinfo['size']
        assert rv.data == objinfo['content']

    def check_html_file_get_404(self, url, objinfo, userinfo, **kwargs):
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_del(self, url, objinfo, userinfo, exists, **kwargs):
        rv = self.open_with_auth(url, 'DELETE',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if exists:
            assert rv.status_code == 204
        else:
            assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_folder_del(self, url, objinfo, userinfo, **kwargs):
        rv = self.open_with_auth(url, 'DELETE',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if url[-1] != '/':
            assert (rv.headers.get('Location') ==
                    'http://localhost%s/' % url)
            self.assert_html_response(rv)
        else:
            assert rv.status_code == 204
            self.assert_html_response(rv)

    def check_html_folder_del_404(self, url, objinfo, userinfo,
                                  exists, parent_exists, **kwargs):
        rv = self.open_with_auth(url, 'DELETE',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_put(self, url, objinfo, userinfo,
                            exists, parent_exists, **kwargs):
        rv = self.open_with_auth(url, 'PUT',
                                 userinfo.name, userinfo.password,
                                 data=objinfo['content'])

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if exists:
            assert rv.status_code == 409
        elif not parent_exists:
            assert rv.status_code == 404
        else:
            assert rv.status_code == 201
        self.assert_html_response(rv)

    def check_html_folder_put(self, url, objinfo, userinfo,
                              exists, parent_exists, **kwargs):
        rv = self.open_with_auth(url, 'PUT',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if exists:
            assert rv.status_code == 409
        elif not parent_exists:
            assert rv.status_code == 404
        else:
            assert rv.status_code == 201
        self.assert_html_response(rv)


class TestStorageApi:
    ContainerType = 'dir'
    FileType = 'file'

    def setup(self):
        app = create_app(__name__)
        app.config['STORAGE'] = 'local'
        self.client = app.test_client()

    def check_storage(self, check_func):
        for (resource,
             userinfo) in product(get_url_list(),
                                  get_user_list()):
            yield (check_func,
                   {
                       'resource': resource,
                       'userinfo': userinfo
                   })

    def test_auth(self):
        for t in self.check_storage(self.check_auth):
            yield t

    def test_stat(self):
        for t in self.check_storage(self.check_stat):
            yield t

    def test_read(self):
        for t in self.check_storage(self.check_read):
            yield t

    def check_auth(self, params):
        from eudat_http_api.http_storage import storage
        userinfo = params['userinfo']

        rv = storage.authenticate(userinfo.name,
                                  userinfo.password)

        if userinfo.valid:
            assert rv is True
        else:
            assert rv is False

    def check_stat(self, params):
        if params['resource'].exists:
            self.check_stat_good(**params)
        else:
            self.check_stat_except(**params)

    def check_stat_good(self, resource, userinfo):
        from eudat_http_api.http_storage import storage

        rv = storage.stat(resource.path)

        if resource.is_dir():
            assert 'children' in rv
            if 'children' in rv:
                assert rv['children'] == resource.objinfo['children']
        elif resource.is_file():
            assert 'size' in rv
            if 'size' in rv:
                assert rv['size'] == resource.objinfo['size']

        assert 'user_metadata' in rv
        if 'user_metadata' in rv:
            assert len(rv['user_metadata']) == 0

    def check_stat_except(self, resource, userinfo):
        from eudat_http_api.http_storage import storage

        assert_raises(storage.NotFoundException,
                      storage.stat,
                      resource.path)

    def check_read(self, params):
        if params['resource'].exists and params['resource'].is_file():
            self.check_read_good(**params)
        else:
            self.check_read_except(**params)

    def check_read_good(self, resource, userinfo):
        from eudat_http_api.http_storage import storage

        gen, fsize, contentlen, rangelist = storage.read(resource.path)

        data = reduce(add, map(lambda (a, b, c, d): d, gen))
        assert data == resource.objinfo['content']
        assert fsize == contentlen
        assert fsize == resource.objinfo['size']
        assert rangelist == []

        #single_range = [[1, 4]]
        #gen, fsize, contentlen, rangelist = storage.read(resource.path,
        #                                                 single_range)

        #data = reduce(add, map(lambda (a, b, c, d): d, gen))
        #assert data == resource.objinfo['content'][1:4+1]
        #assert fsize == resource.objinfo['size']
        #if resource.objinfo['size'] >= 4:
        #    assert contentlen == 4
        #else:
        #    assert contentlen == resource.objinfo['size']

        #assert rangelist == [[1, 4]]

    def check_read_except(self, resource, userinfo):
        from eudat_http_api.http_storage import storage

        if resource.is_dir() and resource.exists:
            assert_raises(storage.IsDirException,
                          storage.read,
                          resource.path)
        elif resource.is_file() and not resource.exists:
            assert_raises(storage.NotFoundException,
                          storage.read,
                          resource.path)
