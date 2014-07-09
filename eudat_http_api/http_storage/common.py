# -*- coding: utf-8 -*-

from __future__ import with_statement

from collections import OrderedDict
import os

from flask import current_app


def get_config_parameter(param_name, default_value=None):
    return current_app.config.get(param_name, default_value)


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


def create_path_links(path):
    """ Create links for each subdirectory in the path.

    This function generates the full path for each subdirectory
    in the given path, and stores it in an ordered dict with the
    subdirectory's basename as key.
    It works for directories or files at the end of the path.

    This can be used to generate links to be displayed in a website.

    Some caveats:
    - if the path has a trailing slash, there will be a phantom empty
        element after the split that we have to ignore.
    - We assume absolute paths, so the first element is always empty.
        Always replace it with a '/'.
    - Intermediate directories must have a trailing slash, so we
        add it manually.
    """
    split = path.split('/')
    ret = OrderedDict()
    agg = ''
    split[0] = '/'
    for item in split[:-1]:
        agg = add_trailing_slash(os.path.join(agg, item))
        ret[item] = agg
    if split[-1] != '':
        item = split[-1]
        agg = os.path.join(agg, item)
        ret[item] = agg
    return ret


class StreamWrapper(object):
    """Wrap the WSGI input so it doesn't store everything in memory.

    taken from http://librelist.com/browser//flask/2011/9/9/any-way-to- \
        stream-file-uploads/#d3f5efabeb0c20e24012605e83ce28ec

    Apparently werkzeug needs a readline method, which I added with
    the same implementation as read.
    """
    def __init__(self, stream):
        self._stream = stream

    def read(self, buffer_size):
        rv = self._stream.read(buffer_size)
        return rv

    def readline(self, buffer_size):
        rv = self._stream.read(buffer_size)
        return rv
