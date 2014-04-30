# -*- coding: utf-8 -*-

from functools import wraps

from flask import abort
from flask import Blueprint
from flask import current_app

from eudat_http_api import auth
from eudat_http_api import common
from eudat_http_api.http_storage import common as http_common
from eudat_http_api.http_storage import cdmi
from eudat_http_api.http_storage import noncdmi
from eudat_http_api.http_storage import json

http_storage_read = Blueprint('http_storage_read', __name__,
                              template_folder='templates')

http_storage_write = Blueprint('http_storage_write', __name__,
                               template_folder='templates')


def choose_access_module():
    access_module = None
    if common.request_is_cdmi():
        if current_app.config.get('ACTIVATE_CDMI', False):
            access_module = cdmi
    elif common.request_wants_json():
        if current_app.config.get('ACTIVATE_JSON', False):
            access_module = json
    else:
        access_module = noncdmi

    return access_module


def check_access_type(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_module = choose_access_module()

        try:
            return f(access_module, *args, **kwargs)
        except AttributeError:
            abort(406)

    return decorated


@http_storage_read.route('/', methods=['GET'], defaults={'objpath': '/'})
@http_storage_read.route('/<path:objpath>', methods=['GET'])
@auth.requires_auth
@check_access_type
def get_obj(access_module, objpath):
    absolute_objpath = http_common.make_absolute_path(objpath)
    if absolute_objpath[-1] == '/':
        return access_module.get_dir_obj(absolute_objpath)
    else:
        return access_module.get_file_obj(absolute_objpath)


@http_storage_write.route('/', methods=['PUT'], defaults={'objpath': '/'})
@http_storage_write.route('/<path:objpath>', methods=['PUT'])
@auth.requires_auth
@check_access_type
def put_obj(access_module, objpath):
    absolute_objpath = http_common.make_absolute_path(objpath)
    if absolute_objpath[-1] == '/':
        return access_module.put_dir_obj(absolute_objpath)
    else:
        return access_module.put_file_obj(absolute_objpath)


@http_storage_write.route('/', methods=['DELETE'], defaults={'objpath': '/'})
@http_storage_write.route('/<path:objpath>', methods=['DELETE'])
@auth.requires_auth
@check_access_type
def del_cdmi_obj(access_module, objpath):
    absolute_objpath = http_common.make_absolute_path(objpath)
    if absolute_objpath[-1] == '/':
        return access_module.del_dir_obj(absolute_objpath)
    else:
        return access_module.del_file_obj(absolute_objpath)


@http_storage_read.errorhandler(403)
@http_storage_write.errorhandler(403)
@check_access_type
def not_authorized_handler(access_module, e):
    try:
        return access_module.not_authorized_handler(e)
    except AttributeError:
        return e, 403
