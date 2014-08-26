# -*- coding: utf-8 -*-

from __future__ import with_statement

import binascii
from collections import OrderedDict
import crcmod
from functools import partial
import os
import random
import struct

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


def get_redirect_host():
    return get_config_parameter('EXTERNAL_HOST', '')


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


def stream_generator(handle, buffer_size=4194304):
    for data in iter(partial(handle.read, buffer_size), ''):
        yield data


def create_object_id_no_ctx(enterprise_number, local_id_length=8):
    """ Facility function that works without an application context."""
    # I agree that the following is ugly and quite probably not as fast
    # as I would like it. Goal is to create a random string with a length
    # of exactly local_id_length.
    local_id_format = ''.join(['%0', str(local_id_length), 'x'])
    local_obj_id = local_id_format % random.randrange(16**local_id_length)

    crc_val = 0
    id_length = str(unichr(8 + len(local_obj_id)))
    # the poly given in the CDMI 1.0.2 spec ()x8005) is wrong,
    # CRC-16 is specified as below
    crc_func = crcmod.mkCrcFun(0x18005, initCrc=0x0000,
                               xorOut=0x0000)

    struct_id = struct.Struct('!cxhccH%ds' % local_id_length)
    packed_id_no_crc = struct_id.pack('\0',
                                      enterprise_number,
                                      '\0',
                                      id_length,
                                      0,
                                      local_obj_id)

    crc_val = crc_func(packed_id_no_crc)

    packed_id = struct_id.pack('\0',
                               enterprise_number,
                               '\0',
                               id_length,
                               crc_val,
                               local_obj_id)

    return packed_id


def create_object_id(local_id_length=8):
    enterprise_number = get_config_parameter('CDMI_ENTERPRISE_NUMBER', 0)
    return create_object_id_no_ctx(enterprise_number, local_id_length)


def create_hex_object_id(local_id_length=8):
    enterprise_number = get_config_parameter('CDMI_ENTERPRISE_NUMBER', 0)
    obj_id = create_object_id_no_ctx(enterprise_number, local_id_length)
    hex_obj_id = binascii.b2a_hex(obj_id)
    return hex_obj_id


def unpack_object_id(obj_id):
    local_id_length = len(obj_id - 8)
    parts = struct.unpack('!cxhccH%ds' % local_id_length, obj_id)
    return parts
