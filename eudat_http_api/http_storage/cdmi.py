# -*- coding: utf-8 -*-

from __future__ import with_statement

import base64
import json
import re

from urlparse import urlparse

from flask import current_app
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import jsonify as flask_jsonify
from flask import json as flask_json
from flask import stream_with_context

from functools import partial
from itertools import imap, chain, islice

from eudat_http_api import common
from eudat_http_api import metadata
from eudat_http_api.common import ContentTypes
from eudat_http_api.http_storage import storage

from eudat_http_api.common import request_wants

class CdmiException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class MalformedArgumentValueException(CdmiException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


cdmi_body_fields = set([
    'objectType',
    'objectId',
    'objectName',
    'parentURI',
    'parentID',
    'domainURI',
    'capabilitiesURI',
    'completionStatus',
    'percentComplete',
    'metadata',
    'exports',
    'snapshots',
    'childrenrange',
    'children',
    'mimetype',
    'metadata',
    'valuerange',
    'valuetransferencoding',
    'value',
    ])

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


def make_absolute_path(path):
    if path != '/':
        return '/%s' % path
    else:
        return '/'


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

    return imap(lambda x: (x.name, json.dumps(
                           {'name': x.name,
                            'path': x.path,
                            'metadata': _safe_stat(x.path, True)
                            })),
                chain(nav_links, dir_gen))


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

        return start, end

    range_requests = []
    cdmi_filters = []
    if request_wants(ContentTypes.cdmi_object):
        try:
            cdmi_filters = _get_cdmi_filters(request.args)
        except MalformedArgumentValueException as e:
            return e.msg, 400
        try:
            range_requests = cdmi_filters['value']
        except KeyError:
            pass
    elif request.headers.get('Range'):
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
    except storage.MalformedPathException as e:
        return e.msg, 400

    response_headers = {'Content-Length': content_len}
    # do not send the content-length to enable
    # transfer-encoding chunked -- do not use chunked to let it
    # work with ROOT, no effect on mem usage anyway
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
                current_app.logger.debug('started a multipart segment')
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

    if request_wants(ContentTypes.cdmi_object):
        if len(range_list) > 1:
            pass  # throw a terrifying exception here, cdmi must not multipart!
        cdmi_json_gen = _get_cdmi_json_file_generator(path,
                                                      wrapped_stream_gen,
                                                      file_size)
        if cdmi_filters:
            filtered_gen = ((a, b(cdmi_filters[a])) for a, b in cdmi_json_gen
                            if a in cdmi_filters)
        else:
            filtered_gen = ((a, b()) for a, b in cdmi_json_gen)

        json_stream_wrapper = _wrap_with_json_generator(filtered_gen)
        return Response(stream_with_context(json_stream_wrapper))

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
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    return 'Created: %d' % (bytes_written), 201


def del_cdmi_file_obj(path):
    """Delete a file through CDMI."""

    try:
        storage.rm(path)
    except storage.IsDirException as e:
        params = urlparse(request.url).query
        return redirect('%s/?%s' % (path, params))
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    empty_response = Response(status=204)
    del empty_response.headers['content-type']
    return empty_response


def get_cdmi_dir_obj(path):
    """Get a directory entry through CDMI.

    Get the listing of a directory.

    TODO: find a way to stream the listing.
    """
    cdmi_filters = []
    if request_wants(ContentTypes.cdmi_object):
        try:
            cdmi_filters = _get_cdmi_filters(request.args)
        except MalformedArgumentValueException as e:
            return e.msg, 400

    try:
        dir_gen = storage.ls(path)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 401
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    if request_wants(ContentTypes.cdmi_object):
        cdmi_json_gen = _get_cdmi_json_dir_generator(path, dir_gen)
        if cdmi_filters:
            filtered_gen = ((a, b(cdmi_filters[a])) for a, b in cdmi_json_gen
                            if a in cdmi_filters)
        else:
            filtered_gen = ((a, b()) for a, b in cdmi_json_gen)

        json_stream_wrapper = _wrap_with_json_generator(filtered_gen)
        return Response(stream_with_context(json_stream_wrapper))

    elif request_wants(ContentTypes.json):
        dir_gen_wrapper = _create_dirlist_gen(dir_gen, path)
        json_stream_wrapper = _wrap_with_json_generator(dir_gen_wrapper)
        return Response(stream_with_context(json_stream_wrapper))
    else:
        return render_template('dirlisting.html',
                               dirlist=dir_gen,
                               path=path,
                               parent_path=common.split_path(path)[0])


def _get_cdmi_filters(args_dict):
    cdmi_args = []
    cdmi_filter = dict()
    for arg_key in args_dict.iterkeys():
        if any(map(lambda s: arg_key.startswith(s), cdmi_body_fields)):
            if re.match('^[\w:-]+(;[\w:-]+)*;?$', arg_key) is None:
                raise MalformedArgumentValueException(
                    'Could not parse the argument expression: %s' % arg_key)

            # remove empty args from ;; or a trailing ;
            cdmi_args = filter(lambda s: s != '', arg_key.split(';'))
            break

    if not cdmi_args:
        return dict()

    re_range = re.compile('(\d+)-(\d+)')
    key, value = None, None
    for arg in cdmi_args:
        try:
            key, value = arg.split(':')
        except ValueError:
            key, value = arg, None
        if key == 'children':
            try:
                value = map(int, re_range.match(value).groups())
                cdmi_filter.update({'childrenrange': value})
            except (AttributeError, TypeError):
                raise MalformedArgumentValueException(
                    'Could not parse value: key: %s - value: %s' % (key, value)
                    )

        elif key == 'value':
            if value is not None:  # remember value can also come without range
                try:
                    value = [map(int, re_range.match(value).groups())]
                except (AttributeError, TypeError):
                    raise MalformedArgumentValueException(
                        'Could not parse value: key: %s - value: %s' % (key, value)
                        )
            else:
                value = []

        cdmi_filter.update({key: value})

    return cdmi_filter


def _get_cdmi_json_file_generator(path, value_gen, file_size):
    return _get_cdmi_json_generator(path, 'object',
                                    value_gen=value_gen,
                                    file_size=file_size)


def _get_cdmi_json_dir_generator(path, list_gen):
    return _get_cdmi_json_generator(path, 'container', dir_listing=list_gen)


def _get_cdmi_json_generator(path, obj_type, **data):
    meta = metadata.stat(path, user_metadata=None)

    def get_range(range_max, range_tuple=(0, None)):
        range_start, range_end = range_tuple
        if range_end is None or range_end > range_max:
            range_end = range_max
        yield '"%s-%s"' % (range_start, range_end)

    def get_usermetadata(path, metadata=None):
        from eudat_http_api import metadata
        yield '%s' % flask_json.dumps(
            metadata.get_user_metadata(path, metadata))

    def wrap_json_string(gen):
        yield '"'
        for part in gen:
            yield base64.b64encode(part)
        yield '"'

    def json_list_gen(iterable, func):
        yield '[\n'
        for i, el in enumerate(iterable):
            if i > 0:
                yield ',\n  "%s"' % func(el)
            else:
                yield '  "%s"' % func(el)
        yield '\n  ]'

    yield ('objectType', lambda x=None: '"application/cdmi-%s"' % obj_type)
    yield ('objectID', lambda x=None: '"%s"' % meta.get('objectID', None))
    yield ('objectName', lambda x=None: '"%s"' % meta.get('name', None))
    yield ('parentURI',
           lambda x=None: '"%s"' % common.add_trailing_slash(
               meta.get('base', None)))
    yield ('parentID', lambda x=None: '"%s"' % meta.get('parentID', None))
    #'domainURI': '%s',
    #'capabilitiesURI': '%s',
    #'completionStatus': '%s',
    #'percentComplete': '%s',  # optional
    yield ('metadata', partial(get_usermetadata, path))
    #'exports': {},  # optional
    #'snapshots': [],  # optional
    if obj_type == 'container':
        yield ('childrenrange', partial(get_range,
                                        meta.get('children', None)))

        yield ('children', lambda t=(0, None): json_list_gen(
            islice(data['dir_listing'], t[0], t[1]), lambda x: x.name))

    if obj_type == 'object':
        yield ('mimetype', lambda x=None: '"mime"')
        yield ('valuerange', partial(get_range, data['file_size']))
        yield ('valuetransferencoding', lambda x=None: '"base64"')
        yield ('value', lambda x=None: wrap_json_string(data['value_gen']))


def _wrap_with_json_generator(gen):
    yield '{\n'
    for i, (key, value) in enumerate(gen):
        if i > 0:
            yield ',\n'
        yield '  "%s": ' % key
        try:
            for part_value in value:
                yield part_value
        except TypeError:
            yield json.dumps(value)

    yield '\n}'


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
    except storage.MalformedPathException as e:
        return e.msg, 400

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
    except storage.MalformedPathException as e:
        return e.msg, 400


    empty_response = Response(status=204)
    del empty_response.headers['content-type']
    return empty_response



def teardown(exception=None):
    return storage.teardown(exception)
