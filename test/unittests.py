from __future__ import with_statement

import base64
from collections import namedtuple
from itertools import product
from operator import add
import os
import re
import shutil
import tempfile

from nose.tools import assert_raises

#from mock import patch
from eudat_http_api import create_app


DB_FD, DB_FILENAME = tempfile.mkstemp()
SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', DB_FILENAME)
DEBUG = True
TESTING = True
STORAGE = 'mock'


class TestHttpRegisterApi:

    def setup(self):
        config = os.getenv('TEST_CONFIG')
        if config is not None:
            app = create_app(config)
        else:
            app = create_app(__name__)
        self.app = app
        with app.app_context():
            from eudat_http_api.registration.models import db
            db.create_all()

        self.client = app.test_client()

    def teardown(self):
        os.close(self.app.config['DB_FD'])
        os.unlink(self.app.config['DB_FILENAME'])

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
        RestResource('/testfile', FileType, {
            'size': 3,
            'content': 'abc',
        }, True, True),
        RestResource('/testfolder', ContainerType, {
            'children': 1,
        }, True, True),
        RestResource('/testfolder/', ContainerType, {
            'children': 1,
        }, True, True),
        RestResource('/testfolder/testfile', FileType, {
            'size': 26,
            'content': 'abcdefghijklmnopqrstuvwxyz',
        }, True, True),
        RestResource('/emptyfolder', ContainerType, {
            'children': 0,
        }, True, True),
        RestResource('/emptyfolder/', ContainerType, {
            'children': 0,
        }, True, True),
        RestResource('/nonfolder', ContainerType, {},
                     False, True),
        RestResource('/testfolder/nonfolder', ContainerType, {},
                     False, True),
        RestResource('/newfolder/newfile', FileType, {
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


def get_local_url_list():
    l = []
    for o in get_url_list():
        o.path = '/tmp/new%s' % o.path
        l.append(o)

    return l


def get_irods_url_list():
    l = []
    for user in [u for u in get_user_list() if u.valid]:
        for o in get_url_list():
            o.path = '/tempZone/home/%s%s' % (user.name, o.path)
            l.append(o)

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


def create_local_urls(url_list):
    for obj in [o for o in url_list if o.exists]:
        if obj.objtype == obj.ContainerType:
            try:
                os.makedirs(obj.path)
            except OSError:
                pass
        elif obj.objtype == obj.FileType:
            try:
                os.makedirs(os.path.split(obj.path)[0])
            except OSError:
                pass
            with open(obj.path, 'wb') as f:
                f.write(obj.objinfo['content'])


def create_irods_env(username, password):
    from os.path import expanduser
    from subprocess import Popen, PIPE

    irods_env_template = """irodsUserName {user}
irodsHost {host}
irodsPort {port}
irodsZone {zone}
"""

    variables = {
        'user': username,
        'host': 'localhost',
        'port': '1247',
        'zone': 'tempZone'
    }

    home_dir = expanduser('~')
    irods_env_dir = '%s/.irods' % home_dir
    irods_env_file = '%s/.irodsEnv' % irods_env_dir
    if not os.path.exists(irods_env_dir):
        os.mkdir(irods_env_dir)

    with open(irods_env_file, 'w') as fd:
        fd.write(irods_env_template.format(**variables))

    p = Popen(['iinit'], stdin=PIPE)
    p.communicate(input='%s\n' % password)


def create_irods_urls(url_list):
    from subprocess import call

    for user in [u for u in get_user_list() if u.valid]:
        create_irods_env(user.name, user.password)
        for obj in [o for o in url_list if o.exists]:
            if obj.objtype == obj.ContainerType:
                call(['imkdir', obj.objtype], shell=True)
            elif obj.objtype == obj.FileType:
                call(['imkdir', os.path.split(obj.objtype)[0]], shell=True)
                fd, filename = tempfile.mkstemp()
                with open(filename, 'wb') as f:
                    f.write(obj.objinfo['content'])

                call(['iput', filename, obj.objtype], shell=True)
                os.remove(filename)


def erase_local_urls(url_list):
    for obj in url_list:
        if obj.objtype == obj.ContainerType:
            try:
                shutil.rmtree(obj.path, ignore_errors=True)
            except OSError:
                raise
        elif obj.objtype == obj.FileType:
            try:
                os.remove(obj.path)
            except OSError:
                pass


def erase_irods_urls(url_list):
    from subprocess import call

    for user in [u for u in get_user_list() if u.valid]:
        create_irods_env(user.name, user.password)
        for obj in url_list:
            try:
                call(['irm -rf', obj.objtype], shell=True)
            except OSError:
                pass


class TestHttpApi:
    ContainerType = 'dir'
    FileType = 'file'

    url_list = None
    client = None
    app = None

    @classmethod
    def setup_class(cls):
        config = os.getenv('TEST_CONFIG')
        if config is not None:
            app = create_app(config)
        else:
            app = create_app(__name__)

        cls.app = app
        cls.test_client = app.test_client()

        cls.url_list = get_url_list()
        if app.config['STORAGE'] == 'local':
            cls.url_list = get_local_url_list()
        elif app.config['STORAGE'] == 'irods':
            cls.url_list = get_irods_url_list()

    def setup(self):
        # this is needed to give each test
        # its own app
        config = os.getenv('TEST_CONFIG')
        if config is not None:
            app = create_app(config)
        else:
            app = create_app(__name__)
        self.client = app.test_client()

        self.app = app

        if self.app.config['STORAGE'] == 'local':
            create_local_urls(self.url_list)
        elif self.app.config['STORAGE'] == 'irods':
            create_irods_urls(self.url_list)

    def teardown(self):
        if self.app.config['STORAGE'] == 'local':
            erase_local_urls(self.url_list)
        elif self.app.config['STORAGE'] == 'irods':
            erase_irods_urls(self.url_list)

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
             userinfo) in product(self.url_list,
                                  get_user_list()):
            yield (check_func,
                   {
                       'url': resource.path,
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

        if (kwargs['objtype'] == self.ContainerType and
                url[-1] != '/'):
            assert (rv.headers.get('Location') ==
                    'http://localhost%s/' % url)
        elif (kwargs['objtype'] == self.ContainerType and
                objinfo['children'] == 0):
            assert rv.status_code == 204
        elif (kwargs['objtype'] == self.ContainerType and
                objinfo['children'] > 0):
            assert rv.status_code == 409
        elif kwargs['objtype'] == self.FileType:
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
    url_list = None
    client = None
    app = None

    @classmethod
    def setup_class(cls):
        config = os.getenv('TEST_CONFIG')
        if config is not None:
            app = create_app(config)
        else:
            app = create_app(__name__)

        cls.app = app

        cls.url_list = get_url_list()
        if app.config['STORAGE'] == 'local':
            cls.url_list = get_local_url_list()
        elif app.config['STORAGE'] == 'irods':
            cls.url_list = get_irods_url_list()

    def setup(self):
        if self.app.config['STORAGE'] == 'local':
            create_local_urls(self.url_list)
        elif self.app.config['STORAGE'] == 'irods':
            create_irods_urls(self.url_list)

    def teardown(self):
        if self.app.config['STORAGE'] == 'local':
            erase_local_urls(self.url_list)
        elif self.app.config['STORAGE'] == 'irods':
            erase_irods_urls(self.url_list)

    def check_storage(self, check_func):
        for (resource,
             userinfo) in product(self.url_list,
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
        with self.app.app_context():
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
        with self.app.app_context():
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

            assert 'user_metadata' not in rv

            # check for a request with metadata disabled
            rv = storage.stat(resource.path, None)

            if resource.is_dir():
                assert 'children' in rv
                if 'children' in rv:
                    assert rv['children'] == resource.objinfo['children']
            elif resource.is_file():
                assert 'size' in rv
                if 'size' in rv:
                    assert rv['size'] == resource.objinfo['size']

            assert 'user_metadata' not in rv

            # check for a request with metadata
            rv = storage.stat(resource.path, True)

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
        with self.app.app_context():
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
        with self.app.app_context():
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
        with self.app.app_context():
            from eudat_http_api.http_storage import storage

            if resource.is_dir() and resource.exists:
                assert_raises(storage.IsDirException,
                              storage.read,
                              resource.path)
            elif resource.is_file() and not resource.exists:
                assert_raises(storage.NotFoundException,
                              storage.read,
                              resource.path)
