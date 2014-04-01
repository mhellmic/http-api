# -*- coding: utf-8 -*-

from __future__ import with_statement

from itertools import chain
import re

from eudat_http_api.http_storage.storage_common import *


"""Test data to use:

    testname, testpass

    /                       children: 3
    /testfile               data: abc, size: 3
    /testfolder             children: 1
    /testfolder/testfile    data: abcdefghijklmnopqrstuvwxyz, size: 26
    /emptyfolder            children: 0
"""


def authenticate(username, password):
    return (username == 'testname' and password == 'testpass')


def stat(path, metadata=None):
    if path == '/testfile':
        if metadata is not None:
            return {'size': 3, 'user_metadata': {}, }
        else:
            return {'size': 3, }
    elif path == '/testfolder/testfile':
        if metadata is not None:
            return {'size': 26, 'user_metadata': {}, }
        else:
            return {'size': 26, }
    elif path == '/':
        if metadata is not None:
            return {'children': 3, 'user_metadata': {}, }
        else:
            return {'children': 3, }
    elif path == '/testfolder' or path == '/testfolder/':
        if metadata is not None:
            return {'children': 1, 'user_metadata': {}, }
        else:
            return {'children': 1, }
    elif path == '/emptyfolder' or path == '/emptyfolder/':
        if metadata is not None:
            return {'children': 0, 'user_metadata': {}, }
        else:
            return {'children': 0, }
    else:
        raise NotFoundException('Path does not exist or is not a file')


def get_user_metadata(path, user_metadata=None):
    return dict()


def set_user_metadata(path, user_metadata):
    pass


def read(path, range_list=[]):
    if path == '/testfile':
        def gen():
            yield (False, 0, 3, 'abc')

        return (gen(), 3, 3, [])
    elif path == '/testfolder/testfile':
        def gen():
            yield (False, 0, 10, 'abcdefghij')
            yield (False, 11, 20, 'klmnopqrst')
            yield (False, 21, 26, 'uvwxyz')

        return (gen(), 26, 26, [])
    elif path == '/':
        raise IsDirException('Path is a directory')
    elif path == '/testfolder' or path == '/testfolder/':
        raise IsDirException('Path is a directory')
    elif path == '/emptyfolder' or path == '/emptyfolder/':
        raise IsDirException('Path is a directory')
    else:
        raise NotFoundException('Path does not exist or is not a file')


def write(path, stream_gen):
    if path == '/testfile':
        raise ConflictException('Path exists')
    elif path == '/testfolder/testfile':
        raise ConflictException('Path exists')
    elif path == '/':
        raise ConflictException('Path exists')
    elif path == '/testfolder' or path == '/testfolder/':
        raise ConflictException('Path exists')
    elif path == '/emptyfolder' or path == '/emptyfolder/':
        raise ConflictException('Path exists')
    elif re.match('^/\w+$', path) is not None:
        return len(list(chain(*stream_gen)))
    elif re.match('^/\w+$', path) is not None:
        return len(list(chain(*stream_gen)))
    elif re.match('^/testfolder/\w+$', path) is not None:
        return len(list(chain(*stream_gen)))
    else:
        raise NotFoundException('Path does not exist or is not a file')


def ls(path):
    if path == '/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/testfolder/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/':
        yield StorageDir('testfolder', '/testfolder')
        yield StorageFile('testfile', '/testfile')
    elif path == '/testfolder' or path == '/testfolder/':
        yield StorageFile('testfile', '/testfolder/testfile')
    elif path == '/emptyfolder' or path == '/emptyfolder/':
        for i in []:  # be an empty generator
            yield i
    else:
        raise NotFoundException('Path does not exist or is not a file')


def mkdir(path):
    if path == '/testfile':
        raise ConflictException('Path exists')
    elif path == '/testfolder/testfile':
        raise ConflictException('Path exists')
    elif path == '/':
        raise ConflictException('Path exists')
    elif path == '/testfolder' or path == '/testfolder/':
        raise ConflictException('Path exists')
    elif path == '/emptyfolder' or path == '/emptyfolder/':
        raise ConflictException('Path exists')
    elif re.match('/\w+/?', path) is not None:
        return True, ''
    elif re.match('/\w+/?', path) is not None:
        return True, ''
    elif re.match('/testfolder/\w+/?', path) is not None:
        return True, ''
    else:
        raise NotFoundException('Path does not exist or is not a file')


def rm(path):
    if path == '/testfile':
        return True, ''
    elif path == '/testfolder/testfile':
        return True, ''
    elif path == '/':
        raise IsDirException('Path is not a file')
    elif path == '/testfolder' or path == '/testfolder/':
        raise IsDirException('Path is not a file')
    elif path == '/emptyfolder' or path == '/emptyfolder/':
        raise IsDirException('Path is not a file')
    else:
        raise NotFoundException('Path does not exist or is not a file')


def rmdir(path):
    if path == '/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/testfolder/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/':
        return True, ''
    elif path == '/testfolder' or path == '/testfolder/':
        return True, ''
    elif path == '/emptyfolder' or path == '/emptyfolder/':
        return True, ''
    else:
        raise NotFoundException('Path does not exist or is not a directory')


def teardown(exception=None):
    pass
