from __future__ import with_statement

from collections import OrderedDict
from flask import request
import os

from http_storage.common import add_trailing_slash


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
