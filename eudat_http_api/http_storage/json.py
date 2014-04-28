# -*- coding: utf-8 -*-

from __future__ import with_statement

from inspect import isgenerator
from itertools import imap, chain

from flask import Response
from flask import json as flask_json
from flask import stream_with_context

from eudat_http_api import metadata
from eudat_http_api.http_storage import common
from eudat_http_api.http_storage import storage


def _wrap_with_json_generator(gen):
    yield '{\n'
    for i, (key, value) in enumerate(gen):
        if i > 0:
            yield ',\n'
        yield '  %s: ' % flask_json.dumps(key)
        if isgenerator(value):
            for part_value in value:
                yield part_value
        else:
            yield flask_json.dumps(value)

    yield '\n}'


def _safe_stat(path, user_metadata):
    try:
        return metadata.stat(path, user_metadata)
    except storage.MalformedPathException:
        return dict()
    except storage.NotFoundException:
        return dict()


def _create_dirlist_gen(dir_gen, path):
    """Returns a list with the directory entries."""
    nav_links = [storage.StorageDir('.', path),
                 storage.StorageDir('..', common.split_path(path)[0])]

    return imap(lambda x: (x.name, flask_json.dumps(
                           {'name': x.name,
                            'path': x.path,
                            'metadata': _safe_stat(x.path, True)
                            })),
                chain(nav_links, dir_gen))


def get_dir_obj(path):
    try:
        dir_gen = storage.ls(path)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 403
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    dir_gen_wrapper = _create_dirlist_gen(dir_gen, path)
    json_stream_wrapper = _wrap_with_json_generator(dir_gen_wrapper)
    buffered_stream = json_stream_wrapper
    #buffered_stream = _wrap_with_buffer(json_stream_wrapper)
    return Response(stream_with_context(buffered_stream))
