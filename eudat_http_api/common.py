# -*- coding: utf-8 -*-

from __future__ import with_statement

import os
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
    json = 'application/json'
    cdmi = ('application/cdmi-object', 'application/cdmi-container')


def request_wants(content_type):
    best = request.accept_mimetypes.best_match([content_type, 'text/html'])
    return (best == content_type and request.accept_mimetypes[best]
            > request.accept_mimetypes['text/html'])


def request_wants_json():
    return request_wants(ContentTypes.json)


def request_wants_cdmi():
    return any(map(request_wants, ContentTypes.cdmi))
