# -*- coding: utf-8 -*-

from __future__ import with_statement

from itertools import chain

from eudat_http_api.http_storage.storage_common import *


def authenticate(username, password):
    return (username == 'testname' and password == 'testpass')


def stat(path, metadata=None):
    return {'size': 10, }


def get_user_metadata(path, user_metadata=None):
    return dict()


def set_user_metadata(path, user_metadata):
    pass


def read(path, range_list=[]):
    def gen():
        yield (False, 0, 3, 'abc')

    return (gen(), 3, 3, [])


def write(path, stream_gen):
    return len(list(chain(*stream_gen)))


def ls(path):
    yield StorageDir('bla', '/tmp/bla')
    yield StorageFile('file', '/tmp/file')


def mkdir(path):
    return True, ''


def rm(path):
    return True, ''


def rmdir(path):
    return True, ''


def teardown(exception=None):
    pass
