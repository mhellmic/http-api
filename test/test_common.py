from __future__ import with_statement

import base64
from collections import namedtuple
from itertools import product
import os
import shutil

from eudat_http_api import create_app
from eudat_http_api.http_storage.common import split_path


class ByteRange:
    start = None
    end = None
    size = None

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __len__(self):
        # include the last byte, too
        return self.end - self.start + 1


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
        self.parent_url, self.name = split_path(self.url)

    def is_dir(self):
        return self.objtype == self.ContainerType

    def is_file(self):
        return self.objtype == self.FileType

    def __str__(self):
        return ('path: %s; type: %s; exists: %s; parent_exists: %s'
                % (self.path,
                   self.objtype,
                   self.exists,
                   self.parent_exists)
                )

    def __repr__(self):
        return self.__str__()


def get_url_list():
    l = [
        # existing objects first
        RestResource('/', RestResource.ContainerType, {
            'children': 3,
            'children_names': ['testfile', 'testfolder', 'emptyfolder']
        }, True, True),
        RestResource('/testfile', RestResource.FileType, {
            'size': 3,
            'content': 'abc',
        }, True, True),
        RestResource('/testfolder', RestResource.ContainerType, {
            'children': 1,
            'children_names': ['testfile']
        }, True, True),
        RestResource('/testfolder/', RestResource.ContainerType, {
            'children': 1,
            'children_names': ['testfile']
        }, True, True),
        RestResource('/testfolder/testfile', RestResource.FileType, {
            'size': 26,
            'content': 'abcdefghijklmnopqrstuvwxyz',
        }, True, True),
        RestResource('/emptyfolder', RestResource.ContainerType, {
            'children': 0,
            'children_names': []
        }, True, True),
        RestResource('/emptyfolder/', RestResource.ContainerType, {
            'children': 0,
            'children_names': []
        }, True, True),
        # not existing objects here
        RestResource('/nonfolder', RestResource.ContainerType, {},
                     False, True),
        RestResource('/testfolder/nonfolder', RestResource.ContainerType, {},
                     False, True),
        RestResource('/nonofile', RestResource.FileType, {
            'size': 10,
            'content': '1234567890',
        }, False, True),
        RestResource('/wrongfilesizefile', RestResource.FileType, {
            'size': 4444,
            'content': '1234567890',
        }, False, True),
        RestResource('/emptyfile', RestResource.FileType, {
            'size': 0,
            'content': '',
        }, False, True),
        # non-existing with non-existing parent here
        RestResource('/newfolder/newfile', RestResource.FileType, {
            'size': 10,
            'content': '1234567890',
        }, False, False),
    ]
    #print 'Testing %d different URLs' % len(l)
    return l


def get_local_url_list():
    l = []
    for o in get_url_list():
        o.path = '/tmp/new%s' % o.path
        l.append(o)

    return l


def get_irods_url_list(rodszone):
    l = []
    for user in [u for u in get_user_list() if u.valid]:
        for o in get_url_list():
            o.path = '/%s/home/%s%s' % (rodszone, user.name, o.path)
            l.append(o)

    return l


def get_user_list():
    User = namedtuple('User', 'name password valid')
    l = [
        User('testname', 'testpass', True),
        User('testname', 'notvalid', False),
        User('notvalidname', 'notvalid', False),
    ]
    #print 'Testing %d different users' % len(l)
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


def create_irods_connection(username, password, rodsconfig):
    from irods import (getRodsEnv, rcConnect, clientLoginWithPassword,
                       rodsErrorName)

    err, rodsEnv = getRodsEnv()  # Override all values later
    rodsEnv.rodsUserName = username

    rodsEnv.rodsHost = rodsconfig[0]
    rodsEnv.rodsPort = rodsconfig[1]
    rodsEnv.rodsZone = rodsconfig[2]

    conn, err = rcConnect(rodsEnv.rodsHost,
                          rodsEnv.rodsPort,
                          rodsEnv.rodsUserName,
                          rodsEnv.rodsZone
                          )

    if err.status != 0:
        raise Exception('Connecting to iRODS failed %s'
                        % rodsErrorName(err.status)[0])

    err = clientLoginWithPassword(conn, password)

    if err != 0:
        raise Exception('Authenticating to iRODS failed %s, user: %, pw: %s'
                        % rodsErrorName(err.status)[0], username, password)

    return conn


def create_irods_urls(url_list, rodsconfig):
    from irods import irodsCollection, irodsOpen

    for user in [u for u in get_user_list() if u.valid]:
        conn = create_irods_connection(user.name, user.password, rodsconfig)
        for obj in [o for o in url_list if o.exists]:
            if obj.objtype == obj.ContainerType:
                base, name = os.path.split(obj.path)
                coll = irodsCollection(conn, base)
                coll.createCollection(name)
            elif obj.objtype == obj.FileType:
                coll = irodsCollection(conn)
                coll.createCollection(os.path.split(obj.path)[0])
                file_handle = irodsOpen(conn, obj.path, 'w')
                if file_handle is not None:
                    file_handle.write(obj.objinfo['content'])
                    file_handle.close()
        conn.disconnect()


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


def erase_irods_urls(url_list, rodsconfig):
    from irods import irodsOpen, irodsCollection

    for user in [u for u in get_user_list() if u.valid]:
        conn = create_irods_connection(user.name, user.password, rodsconfig)
        for obj in url_list:
            file_handle = irodsOpen(conn, obj.path, 'r')
            if file_handle is not None:
                file_handle.close()
                file_handle.delete(force=True)

            base, name = os.path.split(obj.path)
            coll = irodsCollection(conn, base)
            coll.deleteCollection(name)
        conn.disconnect()


class TestApi:
    url_list = None

    @classmethod
    def setup_class(cls):
        config = os.getenv('TEST_CONFIG')
        if config is not None:
            app = create_app(config)
        else:
            app = create_app(__name__)

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

        if app.config['STORAGE'] == 'local':
            create_local_urls(self.url_list)
        elif app.config['STORAGE'] == 'irods':
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

    # from https://gist.github.com/jarus/1160696
    def open_with_auth(self, url, method, username, password,
                       headers={}, data=None):
        combined_headers = headers
        combined_headers.update({
            'Authorization': 'Basic '
            + base64.b64encode(
                username + ":" + password)
        })
        if data:
            return self.client.open(url, method=method,
                                    headers=combined_headers, data=data)
        else:
            return self.client.open(url, method=method,
                                    headers=combined_headers)

    def check_resource(self, check_func):
        for (resource,
             userinfo) in product(self.url_list,
                                  get_user_list()):
            yield (check_func,
                   {
                       'resource': resource,
                       'userinfo': userinfo,
                   })
