# -*- coding: utf-8 -*-

from __future__ import with_statement

from itertools import chain
import re

from eudat_http_api.http_storage.storage_common import *


"""Test data to use:

    testname, testpass

    /                       children: 1
    /tmp/testfile               data: abc, size: 3
    /tmp/testfolder             children: 1
    /tmp/testfolder/testfile    data: abcdefghijklmnopqrstuvwxyz, size: 26
    /tmp/emptyfolder            children: 0
"""


def authenticate(username, password):
    return (username == 'testname' and password == 'testpass')


def stat(path, metadata=None):
    if path == '/tmp/testfile':
        return {'size': 3, }
    elif path == '/tmp/testfolder/testfile':
        return {'size': 26, }
    elif path == '/':
        return {'children': 1, }
    elif path == '/tmp/testfolder' or path == '/tmp/testfolder/':
        return {'children': 1, }
    elif path == '/tmp/emptyfolder' or path == '/tmp/emptyfolder/':
        return {'children': 0, }
    else:
        raise NotFoundException('Path does not exist or is not a file')


def get_user_metadata(path, user_metadata=None):
    return dict()


def set_user_metadata(path, user_metadata):
    pass


def read(path, range_list=[]):
    if path == '/tmp/testfile':
        def gen():
            yield (False, 0, 3, 'abc')

        return (gen(), 3, 3, [])
    elif path == '/tmp/testfolder/testfile':
        def gen():
            yield (False, 0, 10, 'abcdefghij')
            yield (False, 11, 20, 'klmnopqrst')
            yield (False, 21, 26, 'uvwxyz')

        return (gen(), 26, 26, [])
    elif path == '/':
        raise IsDirException('Path is a directory')
    elif path == '/tmp/testfolder' or path == '/tmp/testfolder/':
        raise IsDirException('Path is a directory')
    elif path == '/tmp/emptyfolder' or path == '/tmp/emptyfolder/':
        raise IsDirException('Path is a directory')
    else:
        raise NotFoundException('Path does not exist or is not a file')


def write(path, stream_gen):
    if path == '/tmp/testfile':
        raise ConflictException('Path exists')
    elif path == '/tmp/testfolder/testfile':
        raise ConflictException('Path exists')
    elif path == '/':
        raise ConflictException('Path exists')
    elif path == '/tmp/testfolder' or path == '/tmp/testfolder/':
        raise ConflictException('Path exists')
    elif path == '/tmp/emptyfolder' or path == '/tmp/emptyfolder/':
        raise ConflictException('Path exists')
    elif re.match('^/\w+$', path) is not None:
        return len(list(chain(*stream_gen)))
    elif re.match('^/tmp/\w+$', path) is not None:
        return len(list(chain(*stream_gen)))
    elif re.match('^/tmp/testfolder/\w+$', path) is not None:
        return len(list(chain(*stream_gen)))
    else:
        raise NotFoundException('Path does not exist or is not a file')


def ls(path):
    if path == '/tmp/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/tmp/testfolder/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/':
        yield StorageDir('testfolder', '/tmp/testfolder')
        yield StorageFile('testfile', '/tmp/testfile')
    elif path == '/tmp/testfolder' or path == '/tmp/testfolder/':
        yield StorageFile('testfile', '/tmp/testfolder/testfile')
    elif path == '/tmp/emptyfolder' or path == '/tmp/emptyfolder/':
        for i in []:  # be an empty generator
            yield i
    else:
        raise NotFoundException('Path does not exist or is not a file')


def mkdir(path):
    if path == '/tmp/testfile':
        raise ConflictException('Path exists')
    elif path == '/tmp/testfolder/testfile':
        raise ConflictException('Path exists')
    elif path == '/':
        raise ConflictException('Path exists')
    elif path == '/tmp/testfolder' or path == '/tmp/testfolder/':
        raise ConflictException('Path exists')
    elif path == '/tmp/emptyfolder' or path == '/tmp/emptyfolder/':
        raise ConflictException('Path exists')
    elif re.match('/\w+/?', path) is not None:
        return True, ''
    elif re.match('/tmp/\w+/?', path) is not None:
        return True, ''
    elif re.match('/tmp/testfolder/\w+/?', path) is not None:
        return True, ''
    else:
        raise NotFoundException('Path does not exist or is not a file')


def rm(path):
    if path == '/tmp/testfile':
        return True, ''
    elif path == '/tmp/testfolder/testfile':
        return True, ''
    elif path == '/':
        raise IsDirException('Path is not a file')
    elif path == '/tmp/testfolder' or path == '/tmp/testfolder/':
        raise IsDirException('Path is not a file')
    elif path == '/tmp/emptyfolder' or path == '/tmp/emptyfolder/':
        raise IsDirException('Path is not a file')
    else:
        raise NotFoundException('Path does not exist or is not a file')


def rmdir(path):
    if path == '/tmp/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/tmp/testfolder/testfile':
        raise IsFileException('Path is not a directory')
    elif path == '/':
        return True, ''
    elif path == '/tmp/testfolder' or path == '/tmp/testfolder/':
        return True, ''
    elif path == '/tmp/emptyfolder' or path == '/tmp/emptyfolder/':
        return True, ''
    else:
        raise NotFoundException('Path does not exist or is not a directory')


def teardown(exception=None):
    pass
