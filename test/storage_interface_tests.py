from itertools import product
from operator import add
import os
import tempfile

from mock import patch
from nose.tools import assert_raises

from eudat_http_api import create_app

from eudat_http_api.auth.common import Auth, AuthMethod

from test.test_common import get_local_url_list, get_irods_url_list
from test.test_common import get_user_list
from test.test_common import create_local_urls, create_irods_urls
from test.test_common import erase_local_urls, erase_irods_urls


DB_FD, DB_FILENAME = tempfile.mkstemp()
SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', DB_FILENAME)
DEBUG = True
TESTING = True
STORAGE = 'local'


class TestStorageApi:
    url_list = None

    from collections import namedtuple
    Auth = namedtuple('Auth', 'username password')

    @classmethod
    def setup_class(cls):
        config = os.getenv('TEST_CONFIG')
        if config is not None:
            app = create_app(config)
        else:
            app = create_app(__name__)

        cls.storage_config = app.config['STORAGE']

        if app.config['STORAGE'] == 'local':
            cls.url_list = get_local_url_list()
        elif app.config['STORAGE'] == 'irods':
            with app.app_context():
                cls.url_list = get_irods_url_list(app.config['RODSZONE'])

    def setup(self):
        # this is needed to give each test
        # its own app
        config = os.getenv('TEST_CONFIG')
        if config is not None:
            app = create_app(config)
        else:
            app = create_app(__name__)

        self.app = app
        self.client = app.test_client()

        self.storage_config = app.config['STORAGE']

        if self.app.config['STORAGE'] == 'local':
            create_local_urls(self.url_list)
        elif self.app.config['STORAGE'] == 'irods':
            self.irods_config = (self.app.config['RODSHOST'],
                                 self.app.config['RODSPORT'],
                                 self.app.config['RODSZONE']
                                 )
            with self.app.app_context():
                create_irods_urls(self.url_list,
                                  self.irods_config)

    def teardown(self):
        if self.app.config['STORAGE'] == 'local':
            erase_local_urls(self.url_list)
        elif self.app.config['STORAGE'] == 'irods':
            with self.app.app_context():
                erase_irods_urls(self.url_list,
                                 self.irods_config)

    def check_storage(self, check_func):
        for (resource,
             userinfo) in product(self.url_list,
                                  get_user_list()):

            if self.storage_config == 'local' and not userinfo.valid:
                continue
            yield (check_func,
                   {
                       'resource': resource,
                       'userinfo': userinfo,
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

    def test_ls(self):
        for t in self.check_storage(self.check_ls):
            yield t

    def test_mkdir(self):
        for t in self.check_storage(self.check_mkdir):
            yield t

    def test_rmdir(self):
        for t in self.check_storage(self.check_rmdir):
            yield t

    def test_rm(self):
        for t in self.check_storage(self.check_rm):
            yield t

    def test_write(self):
        for t in self.check_storage(self.check_write):
            yield t

    def check_auth(self, params):
        with self.app.test_request_context():
            from eudat_http_api.http_storage import storage
            userinfo = params['userinfo']

            auth_info = Auth(None)  # the check_auth function is not used
            auth_info.method = AuthMethod.Pass
            auth_info.username = userinfo.name
            auth_info.password = userinfo.password

            rv = storage.authenticate(auth_info)

            if userinfo.valid:
                assert rv is True
            else:
                assert rv is False

    def check_stat(self, params):
        if params['resource'].exists and params['userinfo'].valid:
            self.check_stat_good(**params)
        else:
            self.check_stat_except(**params)

    def check_stat_good(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            rv = storage.stat(resource.path)

            assert hasattr(rv, '__iter__')
            if resource.is_dir():
                assert rv['type'] == storage.DIR
                assert 'children' in rv
                if 'children' in rv:
                    assert rv['children'] == resource.objinfo['children']
            elif resource.is_file():
                assert rv['type'] == storage.FILE
                assert 'size' in rv
                if 'size' in rv:
                    assert rv['size'] == resource.objinfo['size']

            assert 'user_metadata' not in rv

            # check for a request with metadata disabled
            rv = storage.stat(resource.path, None)

            assert hasattr(rv, '__iter__')
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

            assert hasattr(rv, '__iter__')
            if resource.is_dir():
                assert 'children' in rv
                if 'children' in rv:
                    assert rv['children'] == resource.objinfo['children']
            elif resource.is_file():
                assert 'size' in rv
                if 'size' in rv:
                    assert rv['size'] == resource.objinfo['size']

            assert 'user_metadata' in rv
            # have to relax this (again), as travis does not support
            # xattrs needed for the localstorage
            # always assume there is at least the objectID
            #if 'user_metadata' in rv:
            #    assert len(rv['user_metadata']) > 0

    def check_stat_except(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):
            from eudat_http_api.http_storage import storage

            if userinfo.valid:
                assert_raises(storage.NotFoundException,
                              storage.stat,
                              resource.path)
            else:
                assert_raises(storage.NotAuthorizedException,
                              storage.stat,
                              resource.path)

    def check_read(self, params):
        if (params['resource'].exists and params['resource'].is_file() and
                params['userinfo'].valid):
            self.check_read_good(**params)
        else:
            self.check_read_except(**params)

    def check_read_good(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            gen, fsize, contentlen, rangelist = storage.read(resource.path)

            data = reduce(add, map(lambda (a, b, c, d): d, gen))
            assert data == resource.objinfo['content']
            assert fsize == contentlen
            assert fsize == resource.objinfo['size']
            assert rangelist == []

            single_range = [[1, 4]]
            gen, fsize, contentlen, rangelist = storage.read(resource.path,
                                                             single_range)

            data = reduce(add, map(lambda (a, b, c, d): d, gen))
            assert data == resource.objinfo['content'][1:4+1]
            assert fsize == resource.objinfo['size']
            if resource.objinfo['size'] >= 4:
                assert contentlen == 4
                assert rangelist == [(1, 4)]
            else:
                assert contentlen == resource.objinfo['size'] - 1  # no char 0
                assert rangelist == [(1, resource.objinfo['size'])]

    def check_read_except(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            if resource.is_dir() and resource.exists and userinfo.valid:
                assert_raises(storage.IsDirException,
                              storage.read,
                              resource.path)
            elif resource.is_file() and not resource.exists and userinfo.valid:
                assert_raises(storage.NotFoundException,
                              storage.read,
                              resource.path)
            elif not userinfo.valid:
                assert_raises(storage.NotAuthorizedException,
                              storage.read,
                              resource.path)

    def check_ls(self, params):
        if (params['resource'].exists and params['userinfo'].valid and
                params['resource'].is_dir()):
            self.check_ls_good(**params)
        else:
            self.check_ls_except(**params)

    def check_ls_good(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            ls_gen = storage.ls(resource.path)

            ls_res = list(ls_gen)
            assert len(ls_res) == resource.objinfo['children']
            ls_names = map(lambda x: x.name, ls_res)
            assert set(ls_names) == set(resource.objinfo['children_names'])

    def check_ls_except(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            if not userinfo.valid:
                assert_raises(storage.NotAuthorizedException,
                              storage.ls, resource.path)
            elif not resource.exists:
                assert_raises(storage.NotFoundException,
                              storage.ls, resource.path)
            elif not resource.is_dir():
                assert_raises(storage.IsFileException,
                              storage.ls, resource.path)

    def check_mkdir(self, params):
        # there is no distinction between files and dirs.
        # filenames are also used to create directories.
        if (not params['resource'].exists and params['resource'].parent_exists
                and params['userinfo'].valid):
            self.check_mkdir_good(**params)
        else:
            self.check_mkdir_except(**params)

    def check_mkdir_good(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            storage.mkdir(resource.path)

    def check_mkdir_except(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            if not userinfo.valid:
                assert_raises(storage.NotAuthorizedException,
                              storage.mkdir, resource.path)
            elif resource.exists:
                assert_raises(storage.ConflictException,
                              storage.mkdir, resource.path)
            elif not resource.parent_exists:
                assert_raises(storage.NotFoundException,
                              storage.mkdir, resource.path)

    def check_rmdir(self, params):
        if (params['resource'].exists and params['userinfo'].valid and
                params['resource'].is_dir() and
                params['resource'].objinfo['children'] == 0):
            self.check_rmdir_good(**params)
        else:
            self.check_rmdir_except(**params)

    def check_rmdir_good(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            storage.rmdir(resource.path)

    def check_rmdir_except(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            if not userinfo.valid:
                assert_raises(storage.NotAuthorizedException,
                              storage.rmdir, resource.path)
            elif (resource.exists and resource.is_dir() and
                    resource.objinfo['children'] > 0):
                assert_raises(storage.ConflictException,
                              storage.rmdir, resource.path)
            elif not resource.exists:
                assert_raises(storage.NotFoundException,
                              storage.rmdir, resource.path)
            elif resource.is_file():
                assert_raises(storage.IsFileException,
                              storage.rmdir, resource.path)

    def check_rm(self, params):
        if (params['resource'].exists and params['userinfo'].valid and
                params['resource'].is_file()):
            self.check_rm_good(**params)
        else:
            self.check_rm_except(**params)

    def check_rm_good(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            storage.rm(resource.path)

    def check_rm_except(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage

            if not userinfo.valid:
                assert_raises(storage.NotAuthorizedException,
                              storage.rm, resource.path)
            elif not resource.exists:
                assert_raises(storage.NotFoundException,
                              storage.rm, resource.path)
            elif resource.is_dir():
                assert_raises(storage.IsDirException,
                              storage.rm, resource.path)

    def check_write(self, params):
        if (not params['resource'].exists and params['resource'].parent_exists
                and params['userinfo'].valid and params['resource'].is_file()):
            self.check_write_good(**params)
        elif not params['resource'].is_dir():
            self.check_write_except(**params)

    def check_write_good(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage
            file_content = resource.objinfo['content']
            chunk_size = 5

            write_gen = (file_content[i:i+chunk_size]
                         for i in xrange(0, len(file_content), chunk_size))

            write_count = storage.write(resource.path, write_gen)

            assert write_count == len(file_content)

    def check_write_except(self, resource, userinfo):
        with self.app.test_request_context(), \
                patch(
                'eudat_http_api.http_storage.'
                + 'storage_common._get_authentication',
                return_value=self.Auth(userinfo.name, userinfo.password)):

            from eudat_http_api.http_storage import storage
            file_content = resource.objinfo['content']
            chunk_size = 5

            write_gen = (file_content[i:i+chunk_size]
                         for i in xrange(0, len(file_content), chunk_size))

            if not userinfo.valid:
                assert_raises(storage.NotAuthorizedException,
                              storage.write, resource.path, write_gen)
            elif resource.exists:
                assert_raises(storage.ConflictException,
                              storage.write, resource.path, write_gen)
            elif not resource.parent_exists:
                assert_raises(storage.NotFoundException,
                              storage.write, resource.path, write_gen)
