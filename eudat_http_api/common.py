# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import request


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


def request_is_cdmi():
    return 'X-CDMI-Specification-Version' in request.headers
