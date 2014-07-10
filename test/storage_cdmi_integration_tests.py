from base64 import b64encode  # , b64decode
import re
import tempfile

from flask import json

from test.test_common import TestApi
from test.test_common import ByteRange


DB_FD, DB_FILENAME = tempfile.mkstemp()
SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', DB_FILENAME)
DEBUG = True
TESTING = True
STORAGE = 'local'


def string_is_valid_json(value):
    try:
        json.dumps(value)
        return True
    except ValueError:
        return False


def is_valid_objectID(resource, value):
    if value is None:
        return False
    m = re.match('^.*$', value)
    if m is not None:
        return True
    return False


def is_valid_parentID(resource, value):
    # the parent of root is not required
    # to have an objectID
    if resource.is_root:
        return True
    return is_valid_objectID(resource, value)


class TestCdmiApi(TestApi):

    SERVER_CDMI_VERSION = '1.0.2'

    cdmi_mandatory_list = [
        ('objectType', lambda r, v: r.content_type == v),
        ('objectID', lambda r, v: is_valid_objectID(r, v)),
        ('objectName', lambda r, v: r.name == v),
        ('parentURI', lambda r, v: r.parent_url == v),
        ('parentID', lambda r, v: is_valid_parentID(r, v)),
        ('domainURI', lambda r, v: re.match('^/cdmi_domains/.*$', v)),
        ('capabilitiesURI',
            lambda r, v: re.match('^/cdmi_capabilities/.*$', v)),
        ('completionStatus', lambda r, v: re.match('Complete', v)),
        #'percentComplete',
        ('metadata', lambda r, v: string_is_valid_json(v)),
        #'exports',
        #'snapshots',
    ]

    cdmi_container_mandatory_list = cdmi_mandatory_list + [
        ('childrenrange', lambda r, v: re.match('\d+-\d+', v)),
        ('children', lambda r, v: string_is_valid_json(v)),
    ]

    cdmi_object_mandatory_list = cdmi_mandatory_list + [
        ('value', lambda r, v: b64encode(r.objinfo['content']) == v),
        ('valuetransferencoding', lambda r, v: 'base64' == v),
        ('valuerange', lambda r, v: re.match('\d+-\d+', v)),
    ]

    def get_cdmi_versions(self):
        yield '1.0.2'
        yield '1.0.1'

    def check_cdmi_resource(self, check_func):
        for version in self.get_cdmi_versions():
            for func, param_dict in self.check_resource(check_func):
                param_dict['resource'].cdmi_version = version
                if param_dict['resource'].is_dir():
                    param_dict['resource'].content_type = \
                        'application/cdmi-container'
                else:
                    param_dict['resource'].content_type = \
                        'application/cdmi-object'

                yield (func, param_dict)

    def assert_cdmi_response_header(self, rv, resource):
        assert rv.content_type == resource.content_type, \
            'resource content type "%s" does not match "%s"' \
            % (resource.content_type, rv.content_type)
        assert rv.headers.get('X-CDMI-Specification-Version')

    def assert_cdmi_response_body(self, json_data, resource):
        cdmi_mandatory_fields = self.cdmi_mandatory_list
        if resource.content_type == 'application/cdmi-object':
            cdmi_mandatory_fields = self.cdmi_object_mandatory_list
        elif resource.content_type == 'application/cdmi-container':
            cdmi_mandatory_fields = self.cdmi_container_mandatory_list

        for field_name, check_func in cdmi_mandatory_fields:
            # comparing to None is not possible, because None can be a valid
            # value for some fields
            assert json_data.get(field_name, 'ERRCODE') != 'ERRCODE', \
                '%s does not exist' % field_name
            assert check_func(resource, json_data[field_name]), \
                ('%s has wrong value: %s, or type: %s'
                 % (field_name, json_data[field_name],
                    type(json_data[field_name])))

    def test_cdmi_get(self):
        for t in self.check_cdmi_resource(self.check_cdmi_get):
            yield t

    def check_cdmi_get(self, params):
        if params['resource'].is_dir():
            self.check_cdmi_folder_get(**params)
        elif params['resource'].is_file():
            self.check_cdmi_file_get(**params)
            #self.check_cdmi_file_get_partial(**params)

    def check_cdmi_folder_get(self, resource, userinfo):
        cdmi_headers = {
            'Accept': 'application/cdmi-container',
            'X-CDMI-Specification-Version': resource.cdmi_version,
        }
        rv = self.open_with_auth(resource.path, 'GET',
                                 userinfo.name, userinfo.password,
                                 headers=cdmi_headers)

        if not userinfo.valid:
            assert rv.status_code == 403
            return

        if resource.cdmi_version != self.SERVER_CDMI_VERSION:
            assert rv.status_code == 400
            return

        if not resource.exists:
            assert rv.status_code == 404
            return

        if resource.path[-1] != '/':
            assert rv.status_code == 302
            assert (rv.headers.get('Location') == 'http://localhost%s/'
                    % resource.path)
        else:
            json_body = json.loads(rv.data)
            self.assert_cdmi_response_header(rv, resource)
            self.assert_cdmi_response_body(json_body, resource)

    def check_cdmi_file_get(self, resource, userinfo):
        cdmi_headers = {
            'Accept': 'application/cdmi-object',
            'X-CDMI-Specification-Version': resource.cdmi_version,
        }
        rv = self.open_with_auth(resource.path, 'GET',
                                 userinfo.name, userinfo.password,
                                 headers=cdmi_headers)

        if not userinfo.valid:
            assert rv.status_code == 403
            return

        if resource.cdmi_version != self.SERVER_CDMI_VERSION:
            assert rv.status_code == 400
            return

        if not resource.exists:
            assert rv.status_code == 404
            return

        json_body = json.loads(rv.data)
        self.assert_cdmi_response_header(rv, resource)
        self.assert_cdmi_response_body(json_body, resource)
