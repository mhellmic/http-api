# -*- coding: utf-8 -*-

from __future__ import with_statement

import re
from urlparse import urlparse

from flask import current_app
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import stream_with_context

from eudat_http_api.common import create_path_links
from eudat_http_api.http_storage import common
from eudat_http_api.http_storage import storage


class MalformedByteRangeException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


def get_file_obj(path):
    """Get a file from storage through non-CDMI.

    We might want to implement 3rd party copy in
    pull mode here later. That can make introduce
    problems with metadata handling, though.
    """

    def parse_range(range_str):
        start, end = range_str.split('-')

        try:
            if start == '' and end == '':
                start = storage.START
                end = storage.END
            elif start == '' and end != '':
                start = int(end)
                end = storage.BACKWARDS
            elif start != '' and end == '':
                start = int(start)
                end = storage.END
            else:  # start != '' and end != ''
                start = int(start)
                end = int(end)
            start = int(start)
        except ValueError:
            raise MalformedByteRangeException(
                'The byte range provided could not be parsed.')

        return start, end

    range_requests = []
    if request.headers.get('Range'):
        ranges = request.headers.get('Range')
        range_verify_regex = re.compile('^bytes=(\d*-\d*)(,\d*-\d*)*$')
        if range_verify_regex.match(ranges) is None:
            return 'The byte range provided could not be parsed.', 400
        range_regex = re.compile('(\d*-\d*)')
        matches = range_regex.findall(ranges)
        try:
            range_requests = map(parse_range, matches)
        except MalformedByteRangeException as e:
            return e.msg, 400

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
        return e.msg, 403
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

    return Response(stream_with_context(wrapped_stream_gen),
                    headers=response_headers,
                    status=response_status)


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

    return render_template(
        'html/dirlisting.html',
        dirlist=dir_gen,
        path=path,
        path_links=create_path_links(path),
        parent_path=common.add_trailing_slash(common.split_path(path)[0]))


def put_file_obj(path):
    """Put a file into storage.

    request.shallow is set to True at the beginning until after
    the wrapper has been created to make sure that nothing accesses
    the data beforehand.
    I do _not_ know the exact meaning of these things.
    """

    request.shallow = True
    request.environ['wsgi.input'] = \
        common.StreamWrapper(request.environ['wsgi.input'])
    request.shallow = False

    def stream_generator(handle, buffer_size=4194304):
        while True:
            data = handle.read(buffer_size)
            if data == '':
                break
            yield data

    value_gen = stream_generator(request.stream)

    bytes_written = 0
    try:
        bytes_written = storage.write(path, value_gen)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 403
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    return render_template(
        'html/fileput.html',
        uri=path,
        size=bytes_written), 201


def put_dir_obj(path):
    """Put a directory entry.

    Create a directory.
    """

    try:
        storage.mkdir(path)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 403
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    return render_template(
        'html/dirput.html',
        uri=path), 201


def del_file_obj(path):
    """Delete a file."""

    try:
        storage.rm(path)
    except storage.IsDirException as e:
        params = urlparse(request.url).query
        return redirect('%s/?%s' % (path, params))
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 403
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    empty_response = Response(status=204)
    del empty_response.headers['content-type']
    return empty_response


def del_dir_obj(path):
    """Delete a directory."""

    try:
        storage.rmdir(path)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 403
    except storage.ConflictException as e:
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    empty_response = Response(status=204)
    del empty_response.headers['content-type']
    return empty_response
