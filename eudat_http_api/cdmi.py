# -*- coding: utf-8 -*-

from __future__ import with_statement

import re

from urlparse import urljoin, urlparse

from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import jsonify as flask_jsonify
from flask import json as flask_json
from flask import stream_with_context

from eudat_http_api import app
from eudat_http_api import common
from eudat_http_api import metadata
from eudat_http_api import storage


cdmi_container_envelope = {
    'objectType': 'application/cdmi-container',
    'objectId': '%s',
    'objectName': '%s',
    'parentURI': '%s',
    'parentID': '%s',
    'domainURI': '%s',
    'capabilitiesURI': '%s',
    'completionStatus': '%s',
    'percentComplete': '%s',  # optional
    'metadata': {},
    'exports': {},  # optional
    'snapshots': [],  # optional
    'childrenrange': '%s',
    'children': [],  # child container objects end with '/'
    }


cdmi_data_envelope = {
    'objectType': 'application/cdmi-container',
    'objectId': '%s',
    'objectName': '%s',
    'parentURI': '%s',
    'parentID': '%s',
    'domainURI': '%s',
    'capabilitiesURI': '%s',
    'completionStatus': '%s',
    'percentComplete': '%s',  # optional
    'mimetype': '%s',
    'metadata': {},
    'valuerange': '%s',
    'valuetransferencoding': '%s',
    'value': '%s',
    }


def request_wants_cdmi_object():
    """adapted from http://flask.pocoo.org/snippets/45/"""
    best = request.accept_mimetypes \
        .best_match(['application/cdmi-object', 'text/html'])
    return best == 'application/cdmi-object' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


def request_wants_json():
    """from http://flask.pocoo.org/snippets/45/"""
    best = request.accept_mimetypes.best_match(['application/json',
                                                'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


@app.before_request
def check_cdmi():
    if request_wants_cdmi_object():
        g.cdmi = True
        g.cdmi_version = request.headers.get('X-CDMI-Specification-Version')
    else:
        g.cdmi = False


def jsonify():
    return flask_jsonify()


def make_absolute_path(path):
    if path != '/':
        return '/%s' % path
    else:
        return '/'


def create_dirlist_dict(dir_list, path):
    """Returns a dictionary with the directory entries."""
    def make_abs_link(name, path):
        return urljoin(path, name)

    nav_links = [storage.StorageDir('.', path),
                 storage.StorageDir('..', common.split_path(path)[0])]

    return map(lambda x: {'name': x.name,
                          'path': x.path,
                          'metadata': metadata.stat(x.path, True)},
               nav_links + dir_list)


def get_cdmi_file_obj(path):
    """Get a file from storage through CDMI.

    We might want to implement 3rd party copy in
    pull mode here later. That can make introduce
    problems with metadata handling, though.
    """

    def parse_range(range_str):
        start, end = range_str.split('-')
        try:
            start = int(start)
        except:
            start = storage.START

        try:
            end = int(end)
        except:
            end = storage.END

        return (start, end)

    range_requests = []
    if request.headers.get('Range'):
        ranges = request.headers.get('Range')
        range_regex = re.compile('(\d*-\d*)')
        matches = range_regex.findall(ranges)
        range_requests = map(parse_range, matches)

    try:
        (stream_gen,
         file_size,
         content_len,
         range_list) = storage.read(path, range_requests)
    except storage.IsDirException as e:
        params = urlparse(request.url).query
        return redirect('%s/?%s' % (path, params))
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401

    response_headers = {}
    # do not send the content-length to enable
    # transfer-encoding chunked -- do not use chunked to let it
    # work with ROOT, no effect on mem usage anyway
    response_headers['Content-Length'] = content_len
    # Do not try to guess the type
    #response_headers['Content-Type'] = 'application/octet-stream'

    response_status = 200
    multipart = False
    if file_size != content_len:
        response_status = 206
        if len(range_list) > 1:
            multipart = True
        else:
            response_headers['Content-Range'] = ('bytes %d-%d/%d'
                                                 % (range_list[0][0],
                                                    range_list[0][1],
                                                    file_size))

    multipart_frontier = 'frontier'
    if multipart:
        del response_headers['Content-Length']
        response_headers['Content-Type'] = ('multipart/byteranges; boundary=%s'
                                            % multipart_frontier)

    def wrap_multipart_stream_gen(stream_gen, delim, file_size):
        multipart = False
        for segment_size, segment_start, segment_end, data in stream_gen:
            if segment_size:
                multipart = True
                app.logger.debug('started a multipart segment')
                #yield '\n--%s\n\n%s' % (delim, data)
                yield ('\n--%s\n'
                       'Content-Length: %d\n'
                       'Content-Range: bytes %d-%d/%d\n'
                       '\n%s') % (delim, segment_size,
                                  segment_start, segment_end,
                                  file_size, data)
                       #% (delim, segment_size, data)
            else:
                yield data
        if multipart:
            yield '\n--%s--\n' % delim
            # yield 'epilogue'

    wrapped_stream_gen = wrap_multipart_stream_gen(stream_gen,
                                                   multipart_frontier,
                                                   file_size)

    return Response(stream_with_context(wrapped_stream_gen),
                    headers=response_headers,
                    status=response_status)


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


def put_cdmi_file_obj(path):
    """Put a file into storage through CDMI.

    Should also copy CDMI metadata.
    Should support the CDMI put copy from a
    src URL.

    request.shallow is set to True at the beginning until after
    the wrapper has been created to make sure that nothing accesses
    the data beforehand.
    I do _not_ know the exact meaning of these things.
    """

    request.shallow = True
    request.environ['wsgi.input'] = \
        StreamWrapper(request.environ['wsgi.input'])
    request.shallow = False

    def stream_generator(handle, buffer_size=4194304):
        while True:
            data = handle.read(buffer_size)
            if data == '':
                break
            yield data

    gen = stream_generator(request.stream)
    bytes_written = 0
    try:
        bytes_written = storage.write(path, gen)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401
    except storage.StorageException as e:
        return e.msg, 500

    return 'Created: %d' % (bytes_written), 201


def del_cdmi_file_obj(path):
    """Delete a file through CDMI."""

    try:
        storage.rm(path)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500

    if request_wants_cdmi_object():
        empty_response = Response(status=204)
        del empty_response.headers['content-type']
        return empty_response
    elif request_wants_json():
        return flask_jsonify(delete='Deleted: %s' % (path)), 204
    else:
        return 'Deleted: %s' % (path), 204


def get_cdmi_dir_obj(path):
    """Get a directory entry through CDMI.

    Get the listing of a directory.

    TODO: find a way to stream the listing.
    """

    if g.cdmi:
        if request.args.get('metadata', None) is not None:
            return get_cdmi_metadata(path)

    try:
        dir_list = [x for x in storage.ls(path)]
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401
    except storage.StorageException as e:
        return e.msg, 500

    if request_wants_cdmi_object():
        cdmi_json_gen = get_cdmi_json_generator(dir_list, path)
        json_stream_wrapper = wrap_with_json_generator(cdmi_json_gen)
        return Response(stream_with_context(json_stream_wrapper))
    elif request_wants_json():
        return flask_jsonify(dirlist=create_dirlist_dict(dir_list, path))
    else:
        return render_template('dirlisting.html',
                               dirlist=dir_list,
                               path=path,
                               parent_path=common.split_path(path)[0])


def get_cdmi_metadata(path):
    return flask_jsonify(metadata=metadata.stat(path, True))


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


def get_cdmi_json_generator(dir_listing, path):
    meta = metadata.stat(path, True)
    yield ('objectType', '"application/cdmi-container"')
    yield ('objectID', '"%s"' % meta.get('objectID', None))
    yield ('objectName', '"%s"' % meta.get('name', None))
    yield ('parentURI', '"%s"' % meta.get('base', None))
    yield ('parentID', '"%s"' % meta.get('parentID', None))
    #'domainURI': '%s',
    #'capabilitiesURI': '%s',
    #'completionStatus': '%s',
    #'percentComplete': '%s',  # optional
    yield ('metadata', '%s' % flask_json.dumps(meta))
    #'exports': {},  # optional
    #'snapshots': [],  # optional
    yield ('childrenrange', '"0-%s"' % meta.get('children', None))
    yield ('children', json_list_gen(dir_listing, lambda x: x.name))


def wrap_with_json_generator(gen):
    yield '{\n'
    for i, (key, value) in enumerate(gen):
        if i > 0:
            yield ',\n'
        yield '  "%s": ' % key
        try:
            for part_value in value:
                yield part_value
        except TypeError:
            yield value

    yield '\n}'


def json_list_gen(iterable, func):
    yield '[\n'
    for i, el in enumerate(iterable):
        if i > 0:
            yield ',\n  "%s"' % func(el)
        else:
            yield '  "%s"' % func(el)
    yield '\n  ]'


def put_cdmi_dir_obj(path):
    """Put a directory entry through CDMI.

    Create a directory.
    """

    try:
        storage.mkdir(path)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500

    return flask_jsonify(create='Created')


def del_cdmi_dir_obj(path):
    """Delete a directory through CDMI."""

    try:
        storage.rmdir(path)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500

    return flask_jsonify(delete='Deleted: %s' % (path))
