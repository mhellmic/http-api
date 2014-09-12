from __future__ import with_statement

import base64
import binascii
from collections import namedtuple
import crcmod
from itertools import product
import os
import random
import shutil
import struct
import xattr

from eudat_http_api import create_app
from eudat_http_api.http_storage.common import split_path
from eudat_http_api.http_storage.common import add_trailing_slash


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


def create_object_id_no_ctx(enterprise_number, local_id_length=8):
    """ Facility function that works without an application context."""
    # I agree that the following is ugly and quite probably not as fast
    # as I would like it. Goal is to create a random string with a length
    # of exactly local_id_length.
    local_id_format = ''.join(['%0', str(local_id_length), 'x'])
    local_obj_id = local_id_format % random.randrange(16**local_id_length)

    crc_val = 0
    id_length = str(unichr(8 + len(local_obj_id)))
    # the poly given in the CDMI 1.0.2 spec ()x8005) is wrong,
    # CRC-16 is specified as below
    crc_func = crcmod.mkCrcFun(0x18005, initCrc=0x0000,
                               xorOut=0x0000)

    struct_id = struct.Struct('!cxhccH%ds' % local_id_length)
    packed_id_no_crc = struct_id.pack('\0',
                                      enterprise_number,
                                      '\0',
                                      id_length,
                                      0,
                                      local_obj_id)

    crc_val = crc_func(packed_id_no_crc)

    packed_id = struct_id.pack('\0',
                               enterprise_number,
                               '\0',
                               id_length,
                               crc_val,
                               local_obj_id)

    return packed_id


class RestResource:
    ContainerType = 'dir'
    FileType = 'file'

    url = None
    is_root = False
    path = None  # for now path and url are the same
    objtype = None
    objinfo = {}
    exists = None
    parent_exists = None
    objectid = None

    def __init__(self, url,
                 objtype,
                 objinfo,
                 exists=True,
                 parent_exists=True,
                 objectid=None):

        self.url = url
        # this must not be included in add_prefix,
        # since the root is determined without the prefix
        if self.url == '/':
            self.is_root = True
        self.objtype = objtype
        self.objinfo = objinfo
        self.exists = exists
        self.parent_exists = parent_exists
        self.path = self.url
        self.parent_url, self.name = split_path(self.url)
        self.parent_url = add_trailing_slash(self.parent_url)
        if objectid is not None:
            self.objectid = objectid
        else:
            self.objectid = binascii.b2a_hex(create_object_id_no_ctx(20))

    def add_prefix(self, prefix):
        self.url = '%s%s' % (prefix, self.url)
        self.path = self.url
        self.parent_url, self.name = split_path(self.url)
        self.parent_url = add_trailing_slash(self.parent_url)

    def is_dir(self):
        return self.objtype == self.ContainerType

    def is_file(self):
        return self.objtype == self.FileType

    def __str__(self):
        return ('path: %s; type: %s; exists: %s; parent_exists: %s; isroot: %s'
                % (self.path,
                   self.objtype,
                   self.exists,
                   self.parent_exists,
                   self.is_root)
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
        RestResource('/nonfile', RestResource.FileType, {
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
        o.add_prefix('/tmp/new')
        l.append(o)

    return l


def get_local_copy_target_url():
    r = RestResource('/emptyfolder/copied_file', RestResource.FileType, {},
                     True, True)
    r.add_prefix('/tmp/new')

    return r


def get_irods_url_list(rodszone):
    l = []
    for user in [u for u in get_user_list() if u.valid]:
        for o in get_url_list():
            o.add_prefix('/%s/home/%s' % (rodszone, user.name))
            l.append(o)

    return l


def get_irods_copy_target_url(rodszone, userinfo):
    r = RestResource('/emptyfolder/copied_file', RestResource.FileType, {},
                     True, True)
    r.add_prefix('/%s/home/%s' % (rodszone, userinfo.name))

    return r


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
        try:
            attrs = xattr.xattr(obj.path)
            attrs['objectID'] = obj.objectid
        except IOError:
            pass


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
                dir_handle = irodsCollection(conn, obj.path)
                if dir_handle is not None:
                    dir_handle.addUserMetadata('objectID', obj.objectid)
            elif obj.objtype == obj.FileType:
                coll = irodsCollection(conn)
                coll.createCollection(os.path.split(obj.path)[0])
                file_handle = irodsOpen(conn, obj.path, 'w')
                if file_handle is not None:
                    file_handle.write(obj.objinfo['content'])
                    file_handle.addUserMetadata('objectID', obj.objectid)
                    file_handle.close()
        conn.disconnect()


def erase_local_urls(url_list):
    urls = url_list + [get_local_copy_target_url()]
    for obj in urls:
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
        urls = url_list + [get_irods_copy_target_url(
            rodsconfig[2],  # rodszone
            user
        )]
        for obj in urls:
            file_handle = irodsOpen(conn, obj.path, 'w')
            if file_handle is not None:
                file_handle.close()
                file_handle.delete(force=True)
            else:
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

        with app.app_context():
            from eudat_http_api.registration.models import db
            db.create_all()

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

    def get_copy_target_url(self, userinfo):
        if self.app.config['STORAGE'] == 'local':
            return get_local_copy_target_url()
        elif self.app.config['STORAGE'] == 'irods':
            return get_irods_copy_target_url(self.app.config['RODSZONE'],
                                             userinfo)
