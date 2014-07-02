from __future__ import with_statement
from collections import OrderedDict

from flask import request


def create_path_links(path):
    split = path.split('/')
    ret = OrderedDict()
    for i in split[:-1]:
        index = split.index(i)
        if i == '':
            i = '/'
        ret[i] = '/'.join(split[:index + 1]) + '/'
    return ret


class ContentTypes:
    json = 'application/json'
    cdmi = ('application/cdmi-object', 'application/cdmi-container')


def request_wants(content_type):
    best = request.accept_mimetypes.best_match([content_type, 'text/html'])
    return (best == content_type and request.accept_mimetypes[best]
            > request.accept_mimetypes['text/html'])


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


def request_wants_cdmi():
    return any(map(request_wants, ContentTypes.cdmi))


def request_is_cdmi():
    return 'X-CDMI-Specification-Version' in request.headers
