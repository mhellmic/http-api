# -*- coding: utf-8 -*-

from flask import Blueprint

from eudat_http_api.http_storage import cdmi
from eudat_http_api import auth

http_storage_read = Blueprint('http_storage_read', __name__,
                              template_folder='templates')

http_storage_write = Blueprint('http_storage_write', __name__,
                               template_folder='templates')


@http_storage_read.route('/', methods=['GET'], defaults={'objpath': '/'})
@http_storage_read.route('/<path:objpath>', methods=['GET'])
@auth.requires_auth
@cdmi.check_cdmi
def get_cdmi_obj(objpath='/'):
    absolute_objpath = cdmi.make_absolute_path(objpath)
    if absolute_objpath[-1] == '/':
        return cdmi.get_cdmi_dir_obj(absolute_objpath)
    else:
        return cdmi.get_cdmi_file_obj(absolute_objpath)


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
