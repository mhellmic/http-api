# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import current_app
from flask import request

import pydmlite

from eudat_http_api.http_storage.storage_common import *


def authenticate(username, password):
    return True


def stat(path, metadata=None):
    pass


def get_user_metadata(path, user_metadata=None):
    return dict()


def set_user_metadata(path, user_metadata):
    pass


def read(path, range_list=[]):
    pass


def write(path, stream_gen):
    pass


def ls(path):
    pass


def mkdir(path):
    pass


def rm(path):
    pass


def rmdir(path):
    pass
