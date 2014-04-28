# -*- coding: utf-8 -*-

from __future__ import with_statement

import os


def split_path(path):
    if path[-1] == '/':
        return os.path.split(path[:-1])
    else:
        return os.path.split(path)


def add_trailing_slash(path):
    try:
        if path[-1] == '/':
            return path
        else:
            return '%s/' % path
    except IndexError:
        return path
    except TypeError:
        return path


def make_absolute_path(path):
    if path != '/':
        return '/%s' % path
    else:
        return '/'
