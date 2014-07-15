# -*- coding: utf-8 -*-

from __future__ import with_statement

from base64 import b64encode  # , b64decode
import binascii
from collections import deque
import crcmod
from functools import partial
from functools import wraps
#from ijson.backends.yajl2 import parse
from ijson.backends.python import parse
from inspect import isgenerator
from itertools import islice
from itertools import ifilter
import random
import re
import requests
import struct

from urlparse import urlparse

from flask import abort
from flask import Blueprint
from flask import redirect
from flask import request
from flask import Response
from flask import jsonify as flask_jsonify
from flask import json as flask_json
from flask import stream_with_context

from eudat_http_api import auth
from eudat_http_api import metadata
from eudat_http_api.http_storage import common
from eudat_http_api.http_storage import storage
from eudat_http_api.http_storage.common import get_config_parameter


CDMI_VERSION = '1.0.2'


cdmi_uris = Blueprint('cdmi_uris', __name__,
                      template_folder='templates')


def check_cdmi(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        version = request.headers.get('X-CDMI-Specification-Version', None)
        if version != CDMI_VERSION:
            abort(400)

        return f(*args, **kwargs)

    return decorated


@cdmi_uris.route('/cdmi_capabilities/', methods=['GET'])
@auth.requires_auth
@check_cdmi
def get_system_capabilities():
    cdmi_system_capabilities = {
        'cdmi_domains': False,
        'cdmi_queues': False,
        'cdmi_dataobjects': True,
        'cdmi_export_webdav': False,
        #'cdmi_metadata_maxitems': 1024,
        #'cdmi_metadata_maxsize': 4096,
        #'cdmi_metadata_maxtotalsize': 2048,
        'cdmi_security_access_control': False,
        'cdmi_serialization_json': False,
        'cdmi_snapshots': False,
        'cdmi_references': False,
        'cdmi_object_copy_from_local': True,
        'cdmi_object_copy_from_remote': True,
        'cdmi_object_access_by_ID': False,
        }

    cdmi_capabilities_envelope = {
        'objectType': 'application/cdmi-capability',
        'objectID': None,
        'objectName': 'cdmi_capabilities/',
        'parentURI': '/',
        'parentID': None,
        'capabilities': cdmi_system_capabilities,
        'childrenrange': '0-1',
        'children': ['container/', 'dataobject/'],
        }

    return flask_jsonify(cdmi_capabilities_envelope)


@cdmi_uris.route('/cdmi_capabilities/container/', methods=['GET'])
@auth.requires_auth
@check_cdmi
def get_container_capabilities():
    cdmi_container_capabilities = {
        'cdmi_list_children': True,
        'cdmi_list_children_range': True,
        'cdmi_read_metadata': True,
        'cdmi_modify_metadata': False,
        'cdmi_create_dataobject': True,
        'cdmi_post_dataobject': False,
        'cdmi_create_container': True,
        'cdmi_create_reference': False,
        'cdmi_export_container_webdav': False,
        'cdmi_delete_container': True,
        'cdmi_move_container': False,
        'cdmi_copy_container': False,
        'cdmi_move_dataobject': False,
        'cdmi_copy_dataobject': True,
        }

    cdmi_storage_capabilities = {
        'cdmi_size': False,
        }

    cdmi_container_capabilities.update(cdmi_storage_capabilities)

    cdmi_capabilities_envelope = {
        'objectType': 'application/cdmi-capability',
        'objectID': None,
        'objectName': 'container/',
        'parentURI': '/cdmi_capabilities/',
        'parentID': None,
        'capabilities': cdmi_container_capabilities,
        'childrenrange': '0-0',
        'children': [],
        }

    return flask_jsonify(cdmi_capabilities_envelope)


@cdmi_uris.route('/cdmi_capabilities/dataobject/', methods=['GET'])
@auth.requires_auth
@check_cdmi
def get_dataobject_capabilities():
    cdmi_dataobject_capabilities = {
        'cdmi_read_value': True,
        'cdmi_read_value_range': True,
        'cdmi_read_metadata': True,
        'cdmi_modify_value': False,
        'cdmi_modify_value_range': False,
        'cdmi_modify_metadata': False,
        'cdmi_delete_dataobject': True,
        }

    cdmi_storage_capabilities = {
        'cdmi_size': False,
        }

    cdmi_dataobject_capabilities.update(cdmi_storage_capabilities)

    cdmi_capabilities_envelope = {
        'objectType': 'application/cdmi-capability',
        'objectID': None,
        'objectName': 'dataobject/',
        'parentURI': '/cdmi_capabilities/',
        'parentID': None,
        'capabilities': cdmi_dataobject_capabilities,
        'childrenrange': '0-0',
        'children': [],
        }

    return flask_jsonify(cdmi_capabilities_envelope)


@cdmi_uris.route('/cdmi_domains/<domain>')
@auth.requires_auth
def get_domain(domain):
    return flask_jsonify('We dont support domains just yet')


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


class MalformedByteRangeException(CdmiException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class MalformedMsgBodyException(CdmiException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class NotAuthorizedException(CdmiException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


cdmi_body_fields = set([
    'objectType',
    'objectID',
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
    'objectID': '%s',
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
    'objectID': '%s',
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


cdmi_capabilities_envelope = {
    'objectType': 'application/cdmi-capability',
    'objectID': '%s',
    'objectName': '%s',
    'parentURI': '%s',
    'parentID': '%s',
    'capabilities': {},
    'childrenrange': '%s',
    'children': [],  # child container objects end with '/'
    }


def not_authorized_handler(e):
    return e, 403


@check_cdmi
def get_file_obj(path):
    """Get a file from storage through CDMI.

    We might want to implement 3rd party copy in
    pull mode here later. That can make introduce
    problems with metadata handling, though.
    """

    range_requests = []
    cdmi_filters = []
    try:
        cdmi_filters = _get_cdmi_filters(request.args)
    except MalformedArgumentValueException as e:
        return e.msg, 400
    try:
        range_requests = cdmi_filters['value']
        if range_requests:  # if not []
            cdmi_filters['valuerange'] = range_requests[0]

            if len(range_requests) > 1:
                return 'no multipart range allowed', 400
    except KeyError:
        pass

    try:
        (stream_gen,
         file_size,
         content_len,
         range_list) = storage.read(path, range_requests, request.args)
    except storage.IsDirException as e:
        params = urlparse(request.url).query
        return redirect('%s/?%s' % (path, params))
    except storage.RedirectException as e:
        return redirect(e.location, code=e.redir_code)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 403
    except storage.MalformedPathException as e:
        return e.msg, 400

    def wrap_singlepart_stream_gen(stream_gen):
        for _, _, _, data in stream_gen:
            yield data

    wrapped_stream_gen = wrap_singlepart_stream_gen(stream_gen)

    response_headers = {
        'Content-Type': 'application/cdmi-object',
        'X-CDMI-Specification-Version': CDMI_VERSION,
    }
    cdmi_json_gen = _get_cdmi_json_file_generator(path,
                                                  wrapped_stream_gen,
                                                  file_size)
    if cdmi_filters:
        filtered_gen = ((a, b(cdmi_filters[a])) for a, b in cdmi_json_gen
                        if a in cdmi_filters)
    else:
        filtered_gen = ((a, b()) for a, b in cdmi_json_gen)

    json_stream_wrapper = _wrap_with_json_generator(filtered_gen)
    return Response(stream_with_context(json_stream_wrapper),
                    headers=response_headers)


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


@check_cdmi
def put_file_obj(path):
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

    cdmi_json, value_gen = _parse_cdmi_msg_body_fields(request.stream)
    if 'copy' in cdmi_json:
        value_uri = '%s' % cdmi_json['copy']
        user = request.authorization['username']
        pw = request.authorization['password']
        auth = requests.auth.HTTPBasicAuth(user, pw)
        stream = _get_value_stream(value_uri, auth)
        value_gen = common.stream_generator(stream)

    #bytes_written = 0
    try:
        #bytes_written = storage.write(path, value_gen)
        storage.write(path, value_gen)
    except storage.RedirectException as e:
        return redirect(e.location, code=e.redir_code)
    except storage.NotFoundException as e:
        return e.msg, 404
    except storage.NotAuthorizedException as e:
        return e.msg, 403
    except storage.ConflictException as e:
        # this disables updates?
        return e.msg, 409
    except storage.StorageException as e:
        return e.msg, 500
    except storage.MalformedPathException as e:
        return e.msg, 400

    # store the CDMI Object ID
    obj_id = create_object_id()
    hex_obj_id = binascii.b2a_hex(obj_id)
    storage.set_user_metadata(path, {'objectID': hex_obj_id})

    response_headers = {
        'Content-Type': 'application/cdmi-object',
        'X-CDMI-Specification-Version': CDMI_VERSION,
    }
    cdmi_json_gen = _get_cdmi_json_file_generator(path,
                                                  None,
                                                  None)
    cdmi_filters = {
        'objectType': None,
        'objectID': None,
        'objectName': None,
        'parentURI': None,
        'parentID': None,
        'domainURI': None,
        'capabilitiesURI': None,
        'completionStatus': None,
        'mimetype': None,
        'metadata': True,
    }
    filtered_gen = ((a, b(cdmi_filters[a])) for a, b in cdmi_json_gen
                    if a in cdmi_filters)

    json_stream_wrapper = _wrap_with_json_generator(filtered_gen)
    return Response(stream_with_context(json_stream_wrapper),
                    headers=response_headers), 201


def _parse_cdmi_msg_body_fields(handle, buffer_size=4194304):
    """Parses the message body fields of a cdmi request.

    This function parses all fields except the value
    field. It returns a dictionary with the fields and
    a generator that can be used to get the value field.

    It takes advantage that the value field must always
    be the last. An excerpt from the cdmi 1.0.2 spec:
    "The request and response message body JSON fields
     may be specified or returned in any order, with the
     exception that, if present, for data objects, the
     valuerange and value fields shall appear last and
     in that order."

     FIXIT: this first implementation is only partial,
     to accomodate requests that fit in one buffer_size.

    """
    parser = parse(handle)

    data_json = dict()
    value_gen = None

    for prefix, event, value in parser:
        if value == 'value':
            def make_value_gen(val, encoding, buffer_size=4 * 1024):
                """ This function works with the current ijson.

                ijson itself should be modified so that it can return
                an iterator. Then this function will become simpler,
                but will be used to apply any special encoding.
                """
                acc = 0
                out = None
                while out != '':
                    out = val[acc:acc + buffer_size]
                    acc += buffer_size
                    yield out

            pre, eve, val = next(parser)
            value_gen = make_value_gen(
                val,
                data_json.get('valuetransferencoding', None)
            )
            break
        if prefix != '':
            data_json[prefix] = value

    return data_json, value_gen


def _get_value_stream(uri, auth):
    response = requests.get(uri, stream=True, auth=auth)
    if response.status_code > 299:
        print response.status_code
        raise NotAuthorizedException('not authorized at the source')

    return response.raw


@check_cdmi
def del_file_obj(path):
    """Delete a file through CDMI."""

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


@check_cdmi
def get_dir_obj(path):
    """Get a directory entry through CDMI.

    Get the listing of a directory.

    TODO: find a way to stream the listing.
    """
    cdmi_filters = []
    try:
        cdmi_filters = _get_cdmi_filters(request.args)
    except MalformedArgumentValueException as e:
        return e.msg, 400

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

    response_headers = {
        'Content-Type': 'application/cdmi-container',
        'X-CDMI-Specification-Version': CDMI_VERSION,
    }
    cdmi_json_gen = _get_cdmi_json_dir_generator(path, dir_gen)
    if cdmi_filters:
        filtered_gen = ((a, b(cdmi_filters[a])) for a, b in cdmi_json_gen
                        if a in cdmi_filters)
    else:
        filtered_gen = ((a, b()) for a, b in cdmi_json_gen)

    json_stream_wrapper = _wrap_with_json_generator(filtered_gen)
    return Response(stream_with_context(json_stream_wrapper),
                    headers=response_headers)


def _get_cdmi_filters(args_dict):
    return _parse_cdmi_args(_get_cdmi_args(args_dict))


def _get_cdmi_args(args_dict):
    cdmi_args = []
    for arg_key in args_dict.iterkeys():
        if any(map(lambda s: arg_key.startswith(s), cdmi_body_fields)):
            if re.match('^[\w:-]+(;[\w:-]+)*;?$', arg_key) is None:
                raise MalformedArgumentValueException(
                    'Could not parse the argument expression: %s' % arg_key)

            # remove empty args from ;; or a trailing ;
            cdmi_args = ifilter(lambda s: s != '', arg_key.split(';'))
            break

    return cdmi_args


def _parse_cdmi_args(cdmi_args):
    cdmi_filter = dict()

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
                        'Could not parse value: key: %s - value: %s'
                        % (key, value))
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
    base_uri, obj_name = common.split_path(path)
    meta = metadata.stat(path, user_metadata=['objectID'])
    parent_uri = common.add_trailing_slash(base_uri)
    try:
        parent_meta = metadata.stat(base_uri, user_metadata=['objectID'])
    except storage.NotFoundException:
        parent_meta = {}

    def get_range(range_max, range_tuple=(0, None)):
        if range_tuple is None:
            range_start, range_end = 0, None
        else:
            range_start, range_end = range_tuple

        if range_end is None or range_end > range_max:
            range_end = range_max
        yield flask_json.dumps('%s-%s' % (range_start, range_end))

    def get_usermetadata(path, metadata=None):
        from eudat_http_api import metadata
        yield '%s' % flask_json.dumps(
            metadata.get_user_metadata(path, metadata))

    def wrap_json_string(gen):
        yield '"'
        for part in gen:
            yield b64encode(part)
        yield '"'

    def json_list_gen(iterable, func):
        yield '[\n'
        for i, el in enumerate(iterable):
            if i > 0:
                yield ',\n  "%s"' % func(el)
            else:
                yield '  "%s"' % func(el)
        yield '\n  ]'

    def get_hex_object_id_or_none(meta):
        user_meta = meta.get('user_metadata', None)
        if user_meta is not None:
            obj_id = user_meta.get('objectID', None)
            if obj_id is not None:
                # obj_id is already stored in hex
                return obj_id
        return None

    yield ('objectType', lambda x=None: 'application/cdmi-%s' % obj_type)
    yield ('objectID', lambda x=None: get_hex_object_id_or_none(meta))
    yield ('objectName', lambda x=None: obj_name)
    yield ('parentURI', lambda x=None: parent_uri)
    yield ('parentID', lambda x=None: get_hex_object_id_or_none(parent_meta))
    yield ('domainURI', lambda x=None: '/cdmi_domains/%s/'
           % get_config_parameter('CDMI_DOMAIN', None))
    yield ('capabilitiesURI', lambda x=None: '/cdmi_capabilities/%s/'
           % ('dataobject' if obj_type == 'object' else obj_type))
    yield ('completionStatus', lambda x=None: 'Complete')
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
        yield ('mimetype', lambda x=None: 'mime')
        yield ('valuerange', partial(get_range, data['file_size']))
        yield ('valuetransferencoding', lambda x=None: 'base64')
        yield ('value', lambda x=None: wrap_json_string(data['value_gen']))


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


def _wrap_with_buffer(gen, buffer_size=1400):
    print 'buffer wrapping'
    el_size_counter = 0
    buffer_deque = deque()
    for el in gen:
        el_size = len(el)
        if (el_size_counter + el_size) < buffer_size:
            buffer_deque.append(el)
        else:
            output = ''
            try:
                while True:
                    print 'outputting ...'
                    output += buffer_deque.popleft()
            except IndexError:
                pass

            yield output

    output = ''
    try:
        while True:
            print 'outputting at the end...'
            output += buffer_deque.popleft()
    except IndexError:
        pass

    yield output


@check_cdmi
def put_dir_obj(path):
    """Put a directory entry through CDMI.

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

    # store the CDMI Object ID
    obj_id = create_object_id()
    hex_obj_id = binascii.b2a_hex(obj_id)
    storage.set_user_metadata(path, {'objectID': hex_obj_id})

    return flask_jsonify(create='Created'), 201


def del_dir_obj(path):
    """Delete a directory through CDMI."""

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


def unpack_object_id(obj_id):
    local_id_length = len(obj_id - 8)
    parts = struct.unpack('!cxhccH%ds' % local_id_length, obj_id)
    return parts
