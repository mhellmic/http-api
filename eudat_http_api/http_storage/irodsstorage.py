# -*- coding: utf-8 -*-

from __future__ import with_statement

import os

from flask import current_app

from irods import *

from eudat_http_api.auth.common import AuthMethod, AuthException
from eudat_http_api.http_storage import common
from eudat_http_api.http_storage.common import get_config_parameter

from eudat_http_api.http_storage.storage_common import *


class suppress_stdout_stderr(object):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
    This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).

    I took this from
    http://stackoverflow.com/questions/11130156/suppress-stdout-stderr- \
            print-from-python-functions

    + cleaned for PEP8
    + close the save_fds after resetting stdout/err

    Use it:
    with suppress_stdout_stderr():
        irods_function()

    '''
    def __init__(self):
        # Open a pair of null files
        self.null_fds = [open(os.devnull, 'wb') for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0].fileno(), 1)
        os.dup2(self.null_fds[1].fileno(), 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        os.close(self.save_fds[0])
        os.close(self.save_fds[1])
        # Close the null files
        self.null_fds[0].close()
        self.null_fds[1].close()


class IrodsConnection(Connection):
    connection = None

    def __init__(self):
        pass

    def connect(self, auth_info):
        rodsUserName = auth_info.username

        rodsHost = get_config_parameter('RODSHOST')
        rodsPort = get_config_parameter('RODSPORT')
        rodsZone = get_config_parameter('RODSZONE')

        conn, err = rcConnect(rodsHost,
                              rodsPort,
                              rodsUserName,
                              rodsZone
                              )

        if err.status != 0:
            current_app.logger.error('Connecting to iRODS failed %s'
                                     % _getErrorName(err.status))
            raise InternalException('Connecting to iRODS failed')

        with suppress_stdout_stderr():
            err = clientLoginWithPassword(conn, auth_info.password)
        if err == 0:
            current_app.logger.debug('Created a storage connection')
            self.connection = conn
            return True
        else:
            conn.disconnect()
            return False

    def disconnect(self):
        self.connection.disconnect()

    def is_valid(self):
        irods_conn = self.connection
        is_valid = True
        if irods_conn.rError is not None:
            current_app.logger.debug('conn error set to something')
            is_valid = False
        elif irods_conn.loggedIn != 1:  # 1 is logged in
            current_app.logger.debug('conn not logged in: %d'
                                     % irods_conn.loggedIn)
            is_valid = False
        elif irods_conn.status != 0:
            current_app.logger.debug('conn status error: %d'
                                     % irods_conn.status)
            is_valid = False
        return is_valid


connection_pool = ConnectionPool(IrodsConnection)


def authenticate(auth, conn=None):
    """Authenticate with username, password.

    Returns True or False.
    Validates an existing connection.
    """
    if auth.method == AuthMethod.Pass:
        conn = connection_pool.get_connection(auth)
        if conn is not None:
            connection_pool.release_connection(conn)
            return True
        else:
            return False
    return False


def _get_irods_obj_handle(conn, path, mode='r'):
    path_is_dir = False
    obj_handle = _open(conn, path, mode)
    if obj_handle is None:
        obj_handle = irodsCollection(conn, path)
        if int(obj_handle.getId()) >= 0:
            path_is_dir = True
        else:
            raise NotFoundException('Path does not exist')

    return obj_handle, path_is_dir


def _check_conflict(conn, path):
    try:
        f, is_dir = _get_irods_obj_handle(conn, path, 'r')
    except NotFoundException:
        return
    if f is not None:
        if not is_dir:
            _close(f)
        raise ConflictException('Target already exists')


@get_connection(connection_pool)
def stat(path, metadata=None, conn=None):
    """Return detailed information about the object.

    The metadata argument specifies if and which
    user-specified metadata should be read.

    For this, we first have to check if we're reading
    a dir or a file to ask to the right information.

    For the future, there should be a standard what
    stat() returns.
    """

    if conn is None:
        return None

    obj_info = dict()

    obj_handle, path_is_dir = _get_irods_obj_handle(conn, path)

    base, name = common.split_path(path)
    obj_info['base'] = base
    obj_info['name'] = name
    if path_is_dir:
        obj_info['type'] = DIR
        current_app.logger.debug('# of sub collections: %d'
                                 % obj_handle.getLenSubCollections())
        # -1 because irods counts the current dir as subdir, too
        obj_info['children'] = (obj_handle.getLenSubCollections() +
                                obj_handle.getLenObjects() - 1)
        obj_info['ID'] = obj_handle.getId()

    else:
        obj_info['type'] = FILE
        obj_info['size'] = obj_handle.getSize()
        obj_info['resc'] = obj_handle.getResourceName()
        obj_info['repl_num'] = obj_handle.getReplNumber()

    if metadata is not None:
        user_metadata = _get_user_metadata(conn, obj_handle, path, metadata)
        obj_info['user_metadata'] = user_metadata

    try:
        _close(obj_handle)
    except AttributeError:
        pass  # obj is a collection, which cannot be closed

    return obj_info


@get_connection(connection_pool)
def get_user_metadata(path, user_metadata=None, conn=None):
    """Gets user_metadata from irods and filters them by the user_metadata arg.

    see _get_user_metadata
    """

    if conn is None:
        return None

    obj_handle, _ = _get_irods_obj_handle(conn, path)

    user_meta = _get_user_metadata(conn, obj_handle, path, user_metadata)

    try:
        _close(obj_handle)
    except AttributeError:
        pass  # obj is a collection, which cannot be closed

    return user_meta


def _get_user_metadata(conn, obj_handle, path, user_metadata):
    """ get user metadata from irods and filter by the user_metadata argument.

    The user_metadata argument should be an iterable holding the metadata
    key to get. If it's not iterable, this returns all metadata.
    """
    irods_user_metadata = obj_handle.getUserMetadata()
    # convert the irods format into a dict with a single value
    # drop the 'unit' value along the way
    user_meta = dict((key, val) for key, val, unit in irods_user_metadata)

    try:
        # select only the keys that were asked for
        # a combination of:
        # http://stackoverflow.com/questions/18554012/intersecting-two- \
        # dictionaries-in-python
        # http://stackoverflow.com/questions/5352546/best-way-to-extract- \
        # subset-of-key-value-pairs-from-python-dictionary-object
        subset_keys = user_metadata & user_meta.viewkeys()
        sub_user_meta = dict(((k, user_meta[k]) for k in subset_keys))
        user_meta = sub_user_meta
    except TypeError:
        pass

    return user_meta


@get_connection(connection_pool)
def set_user_metadata(path, user_metadata, conn=None):
    """ Set a number of user metadata entries.

    user_metadata should be a dict() holding the metadata keys to set.
    Even though irods supports 2 valu field per metadata item, this
    only sets one.
    If user_metadata is not a dict(), the function throws an exception.
    """

    if conn is None:
        return None

    obj_handle, _ = _get_irods_obj_handle(conn, path)

    _set_user_metadata(conn, obj_handle, user_metadata)

    try:
        _close(obj_handle)
    except AttributeError:
        pass  # obj is a collection, which cannot be closed


def _set_user_metadata(conn, obj_handle, user_metadata):
    """Performs the work for set_user_metadata."""
    for key, val in user_metadata.iteritems():
        obj_handle.addUserMetadata(key, val)


@get_connection(connection_pool)
def read(path, arg_range_list=None, query=None, conn=None):
    """Read a file from the backend storage.

    Returns a bytestream.
    In the case of one range, the bytestream is only
    the specified range.
    In case of multiple ranges, the bytestream is all
    ranges concatenated.
    If a range exceeds the size of the object, the
    bytestream goes until the object end.
    """

    if conn is None:
        return None

    range_list = []
    if arg_range_list is not None:
        range_list = arg_range_list

    file_handle = _open(conn, path, 'r')
    if not file_handle:
        if int(irodsCollection(conn, path).getId()) >= 0:
            raise IsDirException('Path is a directory')
            current_app.logger.error('Path is a directory: %s'
                                     % path)
        else:
            current_app.logger.error('Path does not exist or is not a file: %s'
                                     % path)
            raise NotFoundException('Path does not exist or is not a file')

    file_size = file_handle.getSize()

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


@get_connection(connection_pool)
def write(path, stream_gen, force=False, conn=None):
    """Write a file from an input stream."""

    if conn is None:
        return None

    if not force:
        _check_conflict(conn, path)

    file_handle = _open(conn, path, 'w')
    if not file_handle:
        raise NotFoundException('Path does not exist or is not a file')

    bytes_written = 0
    for chunk in stream_gen:
        bytes_written += file_handle.write(chunk)

    _close(file_handle)

    return bytes_written


@get_connection(connection_pool)
def ls(path, conn=None):
    """Return a generator of a directory listing."""

    if conn is None:
        return None

    coll = irodsCollection(conn)
    coll.openCollection(path)

    # TODO: remove this if it turns out that we don't need it!
    # test if the path actually points to a dir by trying
    # to open it as file. The funtion only returns a file handle
    # if it's a file, None otherwise.
    f = _open(conn, path, 'r')
    if f:
        _close(f)
        raise IsFileException('Path is not a directory')

    if int(coll.getId()) < 0:
        raise NotFoundException('Path does not exist')

    def list_generator(collection):
        for sub in collection.getSubCollections():
            yield StorageDir(sub, os.path.join(path, sub))
        for name, resc in collection.getObjects():
            yield StorageFile(name, os.path.join(path, name), resc)

    gen = list_generator(coll)
    return gen


@get_connection(connection_pool)
def mkdir(path, conn=None):
    """Create a directory."""

    if conn is None:
        return None

    dirname, basename = common.split_path(path)
    coll = irodsCollection(conn)
    coll.openCollection(dirname)

    err = coll.createCollection(basename)
    if err != 0:
        _handle_irodserror(path, err)

    return True, ''


def _handle_irodserror(path, err):
    current_app.logger.error('Irods storage exception: %s: %s'
                             % (path, _getErrorName(err)))

    if err == CAT_UNKNOWN_COLLECTION:
        raise NotFoundException('Path does not exist')
    elif err == CAT_UNKNOWN_FILE:
        raise NotFoundException('Path does not exist')
    elif err == USER_FILE_DOES_NOT_EXIST:
        raise NotFoundException('Path does not exist')
    elif err == CAT_INVALID_AUTHENTICATION:
        raise NotAuthorizedException('Not authorized')
    elif err == CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
        raise ConflictException('Path already exists')
    elif err == CAT_INSUFFICIENT_PRIVILEGE_LEVEL:
        raise NotAuthorizedException('Permission denied')
    elif err == CAT_NAME_EXISTS_AS_DATAOBJ:
        raise ConflictException('Path is not a directory')
    elif err == CAT_NAME_EXISTS_AS_COLLECTION:
        raise ConflictException('Path is a directory')
    elif err == CAT_COLLECTION_NOT_EMPTY:
        raise ConflictException('Path is a directory and not empty')
    elif err == CANT_RM_NON_EMPTY_HOME_COLL:
        raise ConflictException('Path is a directory and not empty')

    raise StorageException('Unknown storage exception')


@get_connection(connection_pool)
def rm(path, conn=None):
    """Delete a file."""

    if conn is None:
        return None

    file_handle = _open(conn, path, 'r')
    if not file_handle:
        if int(irodsCollection(conn, path).getId()) >= 0:
            raise IsDirException('Path is a directory')
        else:
            raise NotFoundException('Path does not exist')

    _close(file_handle)

    err = file_handle.delete(force=True)
    if err != 0:
        if err == CAT_INSUFFICIENT_PRIVILEGE_LEVEL:
            raise NotAuthorizedException('Target creation not allowed')
        else:
            current_app.logger.error('Unknown storage exception: %s: %s'
                                     % (path, _getErrorName(err)))
            raise StorageException('Unknown storage exception')

    return True, ''


@get_connection(connection_pool)
def rmdir(path, force=False, conn=None):
    """Delete a directory.

    Be careful: it also deletes subdirectories
    without asking.
    """

    if conn is None:
        return None

    objinfo = stat(path)
    if not objinfo['type'] == DIR:
        raise IsFileException('Path is a file')

    if not force and objinfo['children'] > 0:
        raise ConflictException('Directory is not empty')

    dirname, basename = common.split_path(path)
    coll = irodsCollection(conn)
    coll.openCollection(dirname)

    err = coll.deleteCollection(basename)
    if err != 0:
        _handle_irodserror(path, err)

    return True, ''


@get_connection(connection_pool)
def copy(srcpath, dstpath, force=False, conn=None):
    """Copy an object locally."""

    if conn is None:
        return None

    if not force:
        _check_conflict(conn, dstpath)

    file_handle = _open(conn, srcpath, 'r')
    if not file_handle:
        raise NotFoundException('Path does not exist or is not a file')

    current_app.logger.debug('argument types to copy(): %s, %s'
                             % (type(dstpath), type(force)))
    err = file_handle.copy(str(dstpath), force)
    if err < 0:  # in case this shows the number of bytes copied
        current_app.logger.debug('copying from %s to %s failed.'
                                 % (srcpath, dstpath))
        _handle_irodserror(srcpath, err)

    _close(file_handle)

    return err


#### Not part of the interface anymore


def _getErrorName(code):
    return rodsErrorName(code)[0]


def _open(conn, path, mode):
    return irodsOpen(conn, path, mode)


def _read(file_handle, buffer_size):
    return file_handle.read(buffSize=buffer_size)


def _seek(file_handle, position):
    return file_handle.seek(position)


def _close(file_handle):
    return file_handle.close()


def _write(file_handle, data):
    return file_handle.write(data)
