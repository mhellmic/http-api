# -*- coding: utf-8 -*-

from __future__ import with_statement

import errno
import os
import stat as sys_stat

from eudat_http_api.storage_common import *


def authenticate(username, password):
    """Authenticate with username, password.

    Returns True or False.
    Validates an existing connection.
    """
    return True


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
        raise NotFoundException('Path does not exist or is not a file: %s'
                                % (path))

    if sys_stat.S_ISDIR(stat_result.st_mode):
        obj_info['children'] = len(os.walk(path).next()[2])
        obj_info['ID'] = None

    else:
        obj_info['size'] = stat_result.st_size
        obj_info['resc'] = None
        obj_info['repl_num'] = 1

    if metadata is not None:
        user_metadata = dict()
        obj_info['user_metadata'] = user_metadata

    return obj_info


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
        file_handle = open(path, 'rb')
    except IOError as e:
        if e.errno == errno.EISDIR:
            raise IsDirException('Path is a directory: %s'
                                 % (path))

        raise NotFoundException('Path does not exist or is not a file: %s'
                                % (path))

    file_size = os.path.getsize(path)

    def adjust_range_size(x, y, file_size):
        if y > file_size:
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

    gen = read_stream_generator(file_handle, file_size, ordered_range_list)

    return gen, file_size, content_len, ordered_range_list


def write(path, stream_gen):
    """Write a file from an input stream."""
    pass


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
        raise NotFoundException('Path does not exist or is not a file: %s'
                                % (path))


def mkdir(path):
    """Create a directory."""
    pass


def rm(path):
    """Delete a file."""
    pass


def rmdir(path):
    """Delete a directory.

    Be careful: it also deletes subdirectories
    without asking.
    """
    pass
