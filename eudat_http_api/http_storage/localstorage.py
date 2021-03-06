# -*- coding: utf-8 -*-

from __future__ import with_statement

import errno
from functools import wraps
from itertools import imap
import os
import shutil
import stat as sys_stat
import xattr

from flask import current_app

from eudat_http_api.auth.common import AuthMethod, AuthException
from eudat_http_api.http_storage.common import get_config_parameter
from eudat_http_api.http_storage.storage_common import *


def check_path_with_exported(path):
    # normpath also removes the trailing slash.
    # since we hand it through for directories, we have
    # to make an exception for that.
    path_end = None
    if len(path) > 1 and path[-1] == '/':
        path_end = -1
    if os.path.normpath(path) != path[:path_end]:
        raise MalformedPathException('Malformed path')

    if any(map(lambda p: path.startswith(p),
               get_config_parameter('EXPORTEDPATHS'))):
        return
    else:
        raise NotFoundException('No such file or directory')


def check_path(f):
    @wraps(f)
    def decorated(path, *args, **kwargs):
        check_path_with_exported(path)
        return f(path, *args, **kwargs)
    return decorated


#def check_auth():
#    auth = _get_authentication()
#    if not authenticate(auth.username, auth.password):
#        raise NotAuthorizedException('Invalid credentials')
#
#
#def with_auth(f):
#    @wraps(f)
#    def decorated(*args, **kwargs):
#        check_auth()
#        return f(*args, **kwargs)
#    return decorated


def authenticate(auth_info):
    """Authenticate with username, password.

    Returns True or False.

    Don't mistake this for real authentication, please.
    It just help tests passing.
    If users are defined in the config, it checks for
    valid accounts and passwords.
    Otherwise it allows everyone.
    """
    if auth_info.method == AuthMethod.Pass:
        current_app.logger.debug('authenticate by PASS: %s'
                                 % auth_info.username)
        if get_config_parameter('USERS') is not None:
            return (auth_info.username in get_config_parameter('USERS') and
                    (get_config_parameter('USERS')[auth_info.username]
                        == auth_info.password))
        else:
            return True
    elif auth_info.method == AuthMethod.Gsi:
        if auth_info.userverifiedok:
            return True
    return False


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
    except (IOError, OSError) as e:
        current_app.logger.debug(e)
        raise NotFoundException('Path does not exist or is not a file')

    if sys_stat.S_ISDIR(stat_result.st_mode):
        obj_info['type'] = DIR
        try:
            obj_info['children'] = len(os.listdir(path))
        except OSError:
            obj_info['children'] = None

    else:
        obj_info['type'] = FILE
        obj_info['size'] = stat_result.st_size

    if metadata is not None:
        user_metadata = get_user_metadata(path, metadata)
        obj_info['user_metadata'] = user_metadata

    return obj_info


@check_path
def get_user_metadata(path, user_metadata=None):
    meta = dict(xattr.xattr(path))
    meta_clean = dict()
    for key, value in meta.iteritems():
        meta_clean[key.replace('user.', '', 1)] = value
    return meta_clean


@check_path
def set_user_metadata(path, user_metadata):
    attrs = xattr.xattr(path)
    try:
        for key, value in user_metadata.iteritems():
            attrs['user.%s' % key] = value
    except IOError:
        raise StorageException('object not modifiable or not found')


@check_path
def read(path, arg_range_list=None, query=None):
    """Read a file from the backend storage.

    Returns a bytestream.
    In the case of one range, the bytestream is only
    the specified range.
    In case of multiple ranges, the bytestream is all
    ranges concatenated.
    If a range exceeds the size of the object, the
    bytestream goes until the object end.
    """

    range_list = []
    if arg_range_list is not None:
        range_list = arg_range_list

    try:
        file_handle = _open(path, 'rb')
    except IOError as e:
        if e.errno == errno.EISDIR:
            raise IsDirException('Path is a directory')

        raise NotFoundException('Path does not exist or is not a file')

    file_size = os.path.getsize(path)

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

    # return the range list without START and END constants
    def replace_length_constants(x, y, file_size):
        if x == START:
            x = 0
        if y == END:
            y = file_size
        return (x, y)

    num_ordered_range_list = map(
        lambda (x, y): replace_length_constants(x, y, file_size),
        ordered_range_list)

    return gen, file_size, content_len, num_ordered_range_list


@check_path
def write(path, stream_gen):
    """Write a file from an input stream."""
    if os.path.exists(path):
        raise ConflictException('Path already exists')

    try:
        write_counter = 0
        with open(path, 'wb') as f:
            for chunk in stream_gen:
                _write(f, chunk)
                write_counter += len(chunk)

        return write_counter
    except IOError as e:
        _handle_oserror(path, e)


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
        return (imap(lambda x: get_obj_type(os.path.join(path, x)),
                     os.listdir(path)))
    except IOError as e:
        _handle_oserror(path, e)
    except OSError as e:
        _handle_oserror(path, e)


@check_path
def mkdir(path):
    """Create a directory."""
    try:
        os.mkdir(path)
    except OSError as e:
        _handle_oserror(path, e)


@check_path
def rm(path):
    """Delete a file."""
    if os.path.isdir(path):
        raise IsDirException('Path is a directory')

    try:
        os.remove(path)
    except OSError as e:
        _handle_oserror(path, e)


@check_path
def rmdir(path):
    """Delete a directory."""
    try:
        os.rmdir(path)
    except OSError as e:
        _handle_oserror(path, e)


@check_path
def copy(srcpath, dstpath, force=False):
    try:
        shutil.copyfile(srcpath, dstpath)
    except OSError as e:
        _handle_oserror(srcpath, e)
    except IOError as e:
        _handle_oserror(srcpath, e)


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


def _handle_oserror(path, e):
    current_app.logger.error('Local storage exception: %s: %s'
                             % (path, e))

    if e.errno == errno.ENOENT:
        raise NotFoundException('Path does not exist')
    elif e.errno == errno.EPERM:
        raise NotAuthorizedException('Not authorized')
    elif e.errno == errno.EEXIST:
        raise ConflictException('Path already exists')
    elif e.errno == errno.EACCES:
        raise NotAuthorizedException('Permission denied')
    elif e.errno == errno.ENOTDIR:
        raise IsFileException('Path is not a directory')
    elif e.errno == errno.EISDIR:
        raise ConflictException('Path is a directory')
    elif e.errno == errno.ENOTEMPTY:
        raise ConflictException('Path is a directory and not empty')

    raise StorageException('Unknown storage exception')
