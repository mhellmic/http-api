# -*- coding: utf-8 -*-

from __future__ import with_statement

import os
from urlparse import urlparse
from flask import request


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


class ContentTypes:
    json, cdmi_object = ('application/json', 'application/cdmi-object')


# in long term move to Flask-Negotiate?

def request_wants(content_type):
    best = request.accept_mimetypes.best_match([content_type, 'text/html'])
    return best == content_type and request.accept_mimetypes[best] > \
           request.accept_mimetypes['text/html']


def request_wants_json():
    return request_wants(ContentTypes.json)


def is_local(storage_url, local_host, local_port, local_zone):
    #This should be part of the storage backend interface
    parsed = urlparse(storage_url)
    if parsed.scheme != 'irods':
        return False
    if parsed.hostname != local_host:
        return False
    if parsed.port != local_port:
        return False
    if local_zone != parsed.path.split('/')[1]:
        return False

    return parsed.path