# -*- coding: utf-8 -*-

from __future__ import with_statement

import os

from flask import g
from flask import request

from irods import *

from eudat_http_api import app
from eudat_http_api import common

from eudat_http_api.storage_common import *


def get_storage():
    """Retrieve a storage connection.

    It fetches one that has been previously
    stored during authentication, else use
    auth info from the request to create one.
    """
    conn = getattr(g, 'storageconn', None)
    if conn is None:
        auth = request.authorization
        try:
            if authenticate(auth.username, auth.password):
                conn = getattr(g, 'storageconn', None)
        except InternalException:
            g.storageconn = None

    return conn


@app.teardown_request
def close_storage(exception=None):
    """Close the storage connection.

    Running this as teardown_request function,
    it probably requires stream_with_context
    """
    conn = getattr(g, 'storageconn', None)
    if conn is not None:
        conn.disconnect()
        app.logger.debug('Disconnected a storage connection')
        g.storageconn = None


def authenticate(username, password):
    """Authenticate with username, password.

    Returns True or False.
    Validates an existing connection.
    """
    err, rodsEnv = getRodsEnv()  # Override all values later
    rodsEnv.rodsUserName = username

    rodsEnv.rodsHost = app.config['RODSHOST']
    rodsEnv.rodsPort = app.config['RODSPORT']
    rodsEnv.rodsZone = app.config['RODSZONE']

    conn, err = rcConnect(rodsEnv.rodsHost,
                          rodsEnv.rodsPort,
                          rodsEnv.rodsUserName,
                          rodsEnv.rodsZone
                          )

    if err.status != 0:
        raise InternalException('Connecting to iRODS failed: %s'
                                % (__getErrorName(err.status)))

    err = clientLoginWithPassword(conn, password)
    if err == 0:
        g.storageconn = conn
        app.logger.debug('Created a storage connection')
        return True
    else:
        return False


def stat(path, metadata=None):
    """Return detailed information about the object.

    The metadata argument specifies if and which
    user-specified metadata should be read.

    For this, we first have to check if we're reading
    a dir or a file to ask to the right information.

    For the future, there should be a standard what
    stat() returns.
    """
    conn = get_storage()

    if conn is None:
        return None

    obj_info = dict()

    path_is_dir = False
    obj_handle = irodsOpen(conn, path, 'r')
    if not obj_handle:
        obj_handle = irodsCollection(conn, path)
        if int(obj_handle.getId()) >= 0:
            path_is_dir = True
        else:
            raise NotFoundException('Path does not exist or is not a file: %s'
                                    % (path))

    base, name = common.split_path(path)
    obj_info['base'] = base
    obj_info['name'] = name
    if path_is_dir:
        obj_info['children'] = (obj_handle.getLenSubCollections() +
                                obj_handle.getLenObjects())
        obj_info['ID'] = obj_handle.getId()

    else:
        obj_info['size'] = obj_handle.getSize()
        obj_info['resc'] = obj_handle.getResourceName()
        obj_info['repl_num'] = obj_handle.getReplNumber()

    if metadata is not None:
        user_metadata = __get_user_metadata(conn, path, metadata)
        obj_info['user_metadata'] = user_metadata

    return obj_info


def get_user_metadata(path, user_metadata=None):
    conn = get_storage()

    if conn is None:
        return None

    return __get_user_metadata(conn, path, user_metadata)


def __get_user_metadata(conn, path, user_metadata):
    obj_handle = irodsOpen(conn, path, 'r')
    if not obj_handle:
        obj_handle = irodsCollection(conn, path)
        if int(obj_handle.getId()) >= 0:
            pass
        else:
            raise NotFoundException('Path does not exist or is not a file: %s'
                                    % (path))

    irods_user_metadata = obj_handle.getUserMetadata()
    # convert the irods format into a dict with a value tuple
    dict_gen = ((key, (val1, val2)) for key, val1, val2 in irods_user_metadata)
    user_meta = dict(dict_gen)

    try:
        # select only the keys that were asked for
        # a combination of:
        # http://stackoverflow.com/questions/18554012/intersecting-two- \
        # dictionaries-in-python
        # http://stackoverflow.com/questions/5352546/best-way-to-extract- \
        # subset-of-key-value-pairs-from-python-dictionary-object
        subset_keys = user_metadata & user_meta.viewkeys()
        sub_user_meta = dict([(k, user_meta[k]) for k in subset_keys])
        user_meta = sub_user_meta
    except TypeError:
        pass

    return user_meta


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
    conn = get_storage()

    if conn is None:
        return None

    file_handle = irodsOpen(conn, path, 'r')
    if not file_handle:
        if int(irodsCollection(conn, path).getId()) >= 0:
            raise IsDirException('Path is a directory: %s'
                                 % (path))
        else:
            raise NotFoundException('Path does not exist or is not a file: %s'
                                    % (path))

    file_size = file_handle.getSize()

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

    def stream_generator(file_handle, file_size,
                         ordered_range_list, buffer_size=4194304):
        """Generate the bytestream.

        Default chunking is 4 MByte.

        Supports multirange request.
        (even unordened and if the ranges overlap)

        In case of no range requests, the whole file is read.

        With range requests, we seek the range, and then deliver
        the bytestream in buffer_size chunks. To stop at the end
        of the range, the make the last buffer smaller.
        This might become a performance issue, as we can have very
        small chunks. Also we deliver differently sized chunks to
        the frontend, and I'm not sure how they take it.

        The special values START and END represent the start and end
        of the file to allow for range requests that only specify
        one the two.

        In case of a multirange request, the delimiter shows when a new
        segment begins (by evaluating to True). It carries also
        information about the segment size.
        """
        multipart = False
        delimiter = False
        print 'range list', ordered_range_list
        if len(ordered_range_list) > 1:
            multipart = True

        if not ordered_range_list:
            while True:
                data = file_handle.read(buffSize=buffer_size)
                if data == '':
                    break
                yield delimiter, 0, file_size, data
        else:
            for start, end in ordered_range_list:
                if start == START:
                    start = 0

                segment_start = start
                segment_end = end

                if end == END:
                    segment_end = file_size
                    file_handle.seek(start)
                    if multipart:
                        delimiter = file_size - start + 1

                    while True:
                        data = file_handle.read(buffSize=buffer_size)
                        if data == '':
                            break
                        yield delimiter, segment_start, segment_end, data
                        delimiter = False
                else:
                    # http expects the last byte included
                    range_size = end - start + 1
                    range_size_acc = 0
                    range_buffer_size = buffer_size
                    file_handle.seek(start)

                    if multipart:
                        delimiter = range_size

                    while range_size_acc < range_size:
                        if (range_size - range_size_acc) < range_buffer_size:
                            range_buffer_size = (range_size - range_size_acc)
                        data = file_handle.read(buffSize=range_buffer_size)
                        if data == '':
                            break
                        yield delimiter, segment_start, segment_end, data
                        delimiter = False
                        range_size_acc += range_buffer_size

        file_handle.close()

    gen = stream_generator(file_handle, file_size, ordered_range_list)
    return gen, file_size, content_len, ordered_range_list


def write(path, stream_gen):
    """Write a file from an input stream."""
    conn = get_storage()

    if conn is None:
        return None

    file_handle = irodsOpen(conn, path, 'w')
    if not file_handle:
        raise NotFoundException('Path does not exist or is not a file: %s'
                                % (path))

    bytes_written = 0
    for chunk in stream_gen:
        bytes_written += file_handle.write(chunk)

    file_handle.close()

    return bytes_written


def ls(path):
    """Return a generator of a directory listing."""
    conn = get_storage()

    if conn is None:
        return None

    coll = irodsCollection(conn)
    coll.openCollection(path)
    # .getId return -1 if the target does not exist or is not
    # a proper collection (e.g. a file)
    if int(coll.getId()) < 0:
        raise NotFoundException('Path does not exist or is not a directory: %s'
                                % (coll.getCollName()))

    # TODO: remove this if it turns out that we don't need it!
    # test if the path actually points to a dir by trying
    # to open it as file. The funtion only returns a file handle
    # if it's a file, None otherwise.
    f = irodsOpen(conn, path, 'r')
    if f:
        f.close()
        raise NotFoundException('Target is not a directory: %s'
                                % (coll.getCollName()))

    def list_generator(collection):
        for sub in collection.getSubCollections():
            sub_slash = '%s/' % sub  # from irods there are no slashes appended
            yield StorageDir(sub_slash, os.path.join(path, sub_slash))
        for name, resc in collection.getObjects():
            yield StorageFile(name, os.path.join(path, name), resc)

    gen = list_generator(coll)
    return gen


def mkdir(path):
    """Create a directory."""
    conn = get_storage()

    if conn is None:
        return None

    dirname, basename = common.split_path(path)
    coll = irodsCollection(conn)
    coll.openCollection(dirname)
    # see ls()
    if coll.getId() < 0:
        raise NotFoundException('Path does not exist or is not a directory: %s'
                                % (coll.getCollName()))

    err = coll.createCollection(basename)
    if err != 0:
        if err == CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
            raise ConflictException('Target already exists: %s'
                                    % (path))
        elif err == CAT_INSUFFICIENT_PRIVILEGE_LEVEL:
            raise NotAuthorizedException('Target creation not allowed: %s'
                                         % (path))
        else:
            raise StorageException('Unknown storage exception: %s: %s'
                                   % (path, __getErrorName(err)))

    return True, ''


def rm(path):
    """Delete a file."""
    conn = get_storage()

    if conn is None:
        return None

    file_handle = irodsOpen(conn, path, 'r')
    if not file_handle:
        raise NotFoundException('Path does not exist or is not a file: %s'
                                % (path))

    file_handle.close()

    err = file_handle.delete(force=True)
    if err != 0:
        if err == CAT_INSUFFICIENT_PRIVILEGE_LEVEL:
            raise NotAuthorizedException('Target creation not allowed: %s'
                                         % (path))
        else:
            raise StorageException('Unknown storage exception: %s: %s'
                                   % (path, __getErrorName(err)))

    return True, ''


def rmdir(path):
    """Delete a directory.

    Be careful: it also deletes subdirectories
    without asking.
    """

    conn = get_storage()

    if conn is None:
        return None

    dirname, basename = common.split_path(path)
    coll = irodsCollection(conn)
    coll.openCollection(dirname)
    # see ls()
    if coll.getId() < 0:
        raise NotFoundException('Path does not exist or is not a directory: %s'
                                % (coll.getCollName()))

    err = coll.deleteCollection(basename)
    if err != 0:
        if err == USER_FILE_DOES_NOT_EXIST:
            raise NotFoundException(
                'Path does not exist or is not a directory: %s'
                % (path))
        elif err == CAT_INSUFFICIENT_PRIVILEGE_LEVEL:
            raise NotAuthorizedException('Target creation not allowed: %s'
                                         % (path))
        else:
            raise StorageException('Unknown storage exception: %s: %s'
                                   % (path, __getErrorName(err)))

    return True, ''


#### Not part of the interface anymore


def __getErrorName(code):
    return rodsErrorName(code)[0]
