# -*- coding: utf-8 -*-

from __future__ import with_statement

from itertools import imap
from functools import partial
from functools import wraps
import os
import pydmlite

from eudat_http_api.http_storage import common
from eudat_http_api.http_storage.storage_common import *


class DmliteConnection(Connection):
    config = None
    pluginmanager = None
    stack = None
    secctx = None
    connection = None

    def __init__(self, config='/etc/dmlite.conf'):
        self.config = config
        # for some connections, only the .connection
        # is passed down. For dmlite, it's the whole
        # object.
        self.connection = self

    def connect(self, username, password):
        pm = pydmlite.PluginManager()
        pm.loadConfiguration(self.config)
        self.pluginmanager = pm
        self.secctx = pydmlite.SecurityContext()
        self.stack = pydmlite.StackInstance(pm)
        return True

    def disconnect(self):
        pass

    def is_valid(self):
        return True


connection_pool = ConnectionPool(DmliteConnection)


def authenticate(username, password):
    return True


def path_to_ascii(f):
    @wraps(f)
    def encode(path, *args, **kwargs):
        return f(path.encode('ascii', 'ignore'), *args, **kwargs)
    return encode


@get_connection(connection_pool)
@path_to_ascii
def stat(path, metadata=None, conn=None):
    catalog = conn.stack.getCatalog()
    xstat = None
    try:
        xstat = catalog.extendedStat(path, True)
    except:
        raise NotFoundException('File not found')

    obj_info = dict()
    base, name = common.split_path(path)
    obj_info['base'] = base
    obj_info['name'] = name

    if xstat.stat.isDir():
        obj_info['type'] = DIR
        obj_info['children'] = xstat.stat.st_size
    else:
        obj_info['type'] = FILE
        obj_info['size'] = xstat.stat.st_size

    return obj_info


@get_connection(connection_pool)
@path_to_ascii
def get_user_metadata(path, user_metadata=None, conn=None):
    return dict()


@get_connection(connection_pool)
@path_to_ascii
def set_user_metadata(path, user_metadata, conn=None):
    pass


@get_connection(connection_pool)
@path_to_ascii
def read(path, range_list=[], query=None, conn=None):
    if path.startswith('/dpm'):
        return _redirect(path, conn)
    else:
        return _read_file(path, range_list, query, conn)


def _redirect(path, conn):
    catalog = conn.stack.getCatalog()
    xstat = None
    try:
        xstat = catalog.extendedStat(path, True)
    except:
        raise NotFoundException('File not found')
    if xstat.stat.isDir():
        raise IsDirException('This is a directory')

    pm = conn.stack.getPoolManager()
    location = pm.whereToRead(path)
    # TODO: support https and custom ports
    # this can come from url.scheme and url.port,
    # but those values can be empty ("" and 0)
    url = location[0].url
    url_str = 'http://%s%s?%s' % (url.domain, url.path, url.queryToString())
    raise RedirectException(url_str, redir_code=307)


def _read_file(path, range_list, query=None, conn=None):
    io = conn.stack.getIODriver()
    iohandler = None
    try:
        iohandler = io.createIOHandler(path, O_RDONLY, query)
    except pydmlite.DmException as e:
        raise

    file_size = iohandler.fstat().st_size

    range_list = imap(lambda (x, y): adjust_range_size(x, y, file_size),
                      range_list)
    ordered_range_list = sorted(range_list)

    if ordered_range_list:
        content_len = sum(imap(lambda (x, y): get_range_size(x, y, file_size),
                               ordered_range_list))
    else:
        content_len = file_size

    gen = read_stream_generator(iohandler, file_size,
                                ordered_range_list,
                                _read, _seek, _close)

    return gen, file_size, content_len, num_ordered_range_list


@get_connection(connection_pool)
@path_to_ascii
def write(path, stream_gen, conn=None):
    pass


@get_connection(connection_pool)
@path_to_ascii
def ls(path, conn=None):
    catalog = conn.stack.getCatalog()

    dir_handle = catalog.openDir(path)

    def list_generator(catalog, dir_handle):
        for xstat in iter(partial(catalog.readDirx, dir_handle), None):
            if xstat.stat.isDir():
                yield StorageDir(xstat.name, os.path.join(path, xstat.name))
            else:
                yield StorageFile(xstat.name, os.path.join(path, xstat.name),
                                  size=xstat.stat.st_size)

    gen = list_generator(catalog, dir_handle)
    return gen


@get_connection(connection_pool)
@path_to_ascii
def mkdir(path, conn=None):
    pass


@get_connection(connection_pool)
@path_to_ascii
def rm(path, conn=None):
    pass


@get_connection(connection_pool)
@path_to_ascii
def rmdir(path, conn=None):
    pass


def _read(iohandler, buffer_size):
    return iohandler.read(buffer_size)


def _seek(iohandler, position):
    return iohandler.seek(position)


def _close(iohandler):
    return iohandler.close()
