# -*- coding: utf-8 -*-

from __future__ import with_statement

import errno
from functools import wraps
import os
import stat as sys_stat
from flask import current_app

from eudat_http_api.http_storage.storage_common import *


def check_path_with_exported(path):
    # normpath also removes the trailing slash.
    # since we hand it through for directories, we have
    # to make an exception for that.
    path_end = None
    if path[-1] == '/':
        path_end = -1
    if os.path.normpath(path) != path[:path_end]:
        raise MalformedPathException('Malformed path')

    if any(map(lambda p: path.startswith(p),
               current_app.config['EXPORTEDPATHS'])):
        return
    else:
        raise NotFoundException('No such file or directory')


def check_path(f):
    @wraps(f)
    def decorated(path, *args, **kwargs):
        check_path_with_exported(path)
        return f(path, *args, **kwargs)

    return decorated


def authenticate(username, password):
    """Authenticate with username, password.

    Returns True or False.
    Validates an existing connection.
    """
    return True


@check_path
def stat(path, metadata=None):
    """Return detailed information about the object.

    The metadata argument specifies if and which
    user-specified metadata should be read.

    For this, we first have to check if we're reading
    a dir or a file to ask to the right information.

    For the future, there should be a standard what
    stat() returns.
    """
    obj_info = dict()

    try:
        stat_result = os.stat(path)
    except IOError:
        raise NotFoundException('Path does not exist or is not a file')

    if sys_stat.S_ISDIR(stat_result.st_mode):
        try:
            obj_info['children'] = len(os.listdir(path))
        except OSError:
            obj_info['children'] = None

    else:
        obj_info['size'] = stat_result.st_size

    if metadata is not None:
        user_metadata = get_user_metadata(path, metadata)
        obj_info['user_metadata'] = user_metadata

    return obj_info


@check_path
def get_user_metadata(path, user_metadata=None):
    return dict()


@check_path
def set_user_metadata(path, user_metadata):
    pass


@check_path
def read(path, range_list=[]):
    """Read a file from the backend storage.

    Returns a bytestream.
    In the case of one range, the bytestream is only
    the specified range.
    In case of multiple ranges, the bytestream is all
    ranges concatenated.
    If a range exceeds the size of the object, the
    bytestream goes until the object end.
    """

    try:
        file_handle = _open(path, 'rb')
    except IOError as e:
        if e.errno == errno.EISDIR:
            raise IsDirException('Path is a directory')

        raise NotFoundException('Path does not exist or is not a file')

    file_size = os.path.getsize(path)

    def adjust_range_size(x, y, file_size):
        if y >= file_size:
            y = END
        return (x, y)

    def get_range_size(x, y, file_size):
        if x == START:
            x = 0
        if y == END:
            y = file_size - 1  # because we adjust all other sizes below
        return y - x + 1  # http expects the last byte included

    range_list = map(lambda (x, y): adjust_range_size(x, y, file_size),
                     range_list)
    ordered_range_list = sorted(range_list)

    if ordered_range_list:
        content_len = sum(map(lambda (x, y): get_range_size(x, y, file_size),
                              ordered_range_list))
    else:
        content_len = file_size

    gen = read_stream_generator(file_handle, file_size,
                                ordered_range_list,
                                _read, _seek, _close)

    return gen, file_size, content_len, ordered_range_list


@check_path
def write(path, stream_gen):
    """Write a file from an input stream."""
    return 0


@check_path
def ls(path):
    """Return a generator of a directory listing."""

    def get_obj_type(path):
        basedir, name = os.path.split(path)
        if os.path.isfile(path):
            return StorageFile(name, path)
        else:
            return StorageDir(name, path)

    try:
        return (map(lambda x: get_obj_type(os.path.join(path, x)),
                    os.listdir(path)))
    except IOError:
        raise NotFoundException('Path does not exist or is not a file')


@check_path
def mkdir(path):
    """Create a directory."""
    os.makedirs(path)


@check_path
def rm(path):
    """Delete a file."""
    os.remove(path)


@check_path
def rmdir(path):
    """Delete a directory.

    Be careful: it also deletes subdirectories
    without asking.
    """
    os.removedirs(path)


def teardown(exception=None):
    pass


def _open(path, mode):
    return open(path, mode)


def _read(file_handle, buffer_size):
    return file_handle.read(buffer_size)


def _seek(file_handle, position):
    return file_handle.seek(position)


def _close(file_handle):
    return file_handle.close()


def _write(file_handle, data):
    return file_handle.write(data)
