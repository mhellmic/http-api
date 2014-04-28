# -*- coding: utf-8 -*-

from functools import wraps
from flask import Blueprint

from eudat_http_api import common
from eudat_http_api.http_storage import cdmi
from eudat_http_api.http_storage import noncdmi
from eudat_http_api import auth

http_storage_read = Blueprint('http_storage_read', __name__,
                              template_folder='templates')

http_storage_write = Blueprint('http_storage_write', __name__,
                               template_folder='templates')


def check_access_type(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_module = None
        if common.request_is_cdmi():
            access_module = cdmi
        else:
            access_module = noncdmi

        return f(access_module, *args, **kwargs)

    return decorated


@http_storage_read.route('/', methods=['GET'], defaults={'objpath': '/'})
@http_storage_read.route('/<path:objpath>', methods=['GET'])
@auth.requires_auth
@cdmi.check_cdmi
def get_obj(access_module, objpath='/'):
    absolute_objpath = cdmi.make_absolute_path(objpath)
    if absolute_objpath[-1] == '/':
        return access_module.get_dir_obj(absolute_objpath)
    else:
        return access_module.get_file_obj(absolute_objpath)


@http_storage_write.route('/', methods=['PUT'], defaults={'objpath': '/'})
@http_storage_write.route('/<path:objpath>', methods=['PUT'])
@auth.requires_auth
@cdmi.check_cdmi
def put_cdmi_obj(objpath):
    absolute_objpath = cdmi.make_absolute_path(objpath)
    if absolute_objpath[-1] == '/':
        return cdmi.put_cdmi_dir_obj(absolute_objpath)
    else:
        return cdmi.put_cdmi_file_obj(absolute_objpath)


@http_storage_write.route('/', methods=['DELETE'], defaults={'objpath': '/'})
@http_storage_write.route('/<path:objpath>', methods=['DELETE'])
@auth.requires_auth
@cdmi.check_cdmi
def del_cdmi_obj(objpath):
    absolute_objpath = cdmi.make_absolute_path(objpath)
    if absolute_objpath[-1] == '/':
        return cdmi.del_cdmi_dir_obj(absolute_objpath)
    else:
        return cdmi.del_cdmi_file_obj(absolute_objpath)


@http_storage_read.errorhandler(403)
@http_storage_write.errorhandler(403)
def not_authorized_handler(e):
    return cdmi.not_authorized_handler(e)


@http_storage_read.teardown_request
@http_storage_write.teardown_request
def teardown(exception=None):
    return cdmi.teardown(exception)
