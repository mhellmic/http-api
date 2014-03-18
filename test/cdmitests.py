from mock import patch
from nose.tools import assert_raises

import json

from eudat_http_api import create_app


STORAGE = 'local'
DEBUG = True
TESTING = True


class TestCDMI:
    client = None
    cdmi_mandatory_list = [
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
    ]

    cdmi_container_mandatory_list = cdmi_mandatory_list + [
        'childrenrange',
        'children',
    ]

    cdmi_object_mandatory_list = cdmi_mandatory_list + [
        'value',
        'valuetransferencoding',
        'valuerange',
    ]

    def setup(self):
        app = create_app(__name__)
        self.client = app.test_client()

    def get_dirlist_entry_info(self, dirlist):
        return map(lambda (x, y): json.loads(y), dirlist)

    def test_create_dirlist_dict_empty(self):
        from eudat_http_api.http_storage import cdmi

        with patch('eudat_http_api.metadata.stat', return_value={}):
            result = list(cdmi._create_dirlist_gen([], '/home/'))
            assert len(result) == 2
            entry_info = self.get_dirlist_entry_info(result)
            assert entry_info[0]['path'] == '/home/'
            assert entry_info[0]['name'] == '.'
            assert entry_info[1]['path'] == '/'
            assert entry_info[1]['name'] == '..'

            result = list(cdmi._create_dirlist_gen([], '/home'))
            assert len(result) == 2
            entry_info = self.get_dirlist_entry_info(result)
            assert entry_info[0]['path'] == '/home'
            assert entry_info[0]['name'] == '.'
            assert entry_info[1]['path'] == '/'
            assert entry_info[1]['name'] == '..'

            result = list(cdmi._create_dirlist_gen([], '/'))
            assert len(result) == 2
            entry_info = self.get_dirlist_entry_info(result)
            assert entry_info[0]['path'] == '/'
            assert entry_info[0]['name'] == '.'
            assert entry_info[1]['path'] == ''
            assert entry_info[1]['name'] == '..'

    def test_create_dirlist_dict_one_dir(self):
        from eudat_http_api.http_storage import cdmi
        from eudat_http_api.http_storage import storage

        with patch('eudat_http_api.metadata.stat', return_value={}):
            result = list(cdmi._create_dirlist_gen(
                [storage.StorageDir('test', '/home/test/')],
                '/home/'))
            assert len(result) == 3
            entry_info = self.get_dirlist_entry_info(result)
            assert entry_info[0]['name'] == '.'
            assert entry_info[1]['name'] == '..'
            assert entry_info[2]['path'] == '/home/test/'
            assert entry_info[2]['name'] == 'test'

            result = list(cdmi._create_dirlist_gen(
                [storage.StorageDir('test', '/home/test')],
                '/home/'))
            assert len(result) == 3
            entry_info = self.get_dirlist_entry_info(result)
            assert entry_info[0]['name'] == '.'
            assert entry_info[1]['name'] == '..'
            assert entry_info[2]['path'] == '/home/test'
            assert entry_info[2]['name'] == 'test'

    def test_create_dirlist_dict_one_file(self):
        from eudat_http_api.http_storage import cdmi
        from eudat_http_api.http_storage import storage

        with patch('eudat_http_api.metadata.stat', return_value={}):
            result = list(cdmi._create_dirlist_gen(
                [storage.StorageDir('test', '/home/test')],
                '/home/'))
            assert len(result) == 3
            entry_info = self.get_dirlist_entry_info(result)
            assert entry_info[0]['name'] == '.'
            assert entry_info[1]['name'] == '..'
            assert entry_info[2]['path'] == '/home/test'
            assert entry_info[2]['name'] == 'test'

    def test_get_cdmi_filters_valid_single(self):
        from eudat_http_api.http_storage import cdmi

        result = cdmi._get_cdmi_filters({})
        assert result == {}

        result = cdmi._get_cdmi_filters({'non_cdmi_argument': None})
        assert len(result) == 0

        result = cdmi._get_cdmi_filters({'children:2-10': None})
        assert len(result) == 2
        assert 'children' in result
        assert 'childrenrange' in result
        assert result['children'] == [2, 10]
        assert result['childrenrange'] == [2, 10]

        result = cdmi._get_cdmi_filters({'value:2-10': None})
        assert len(result) == 1
        assert 'value' in result
        assert result['value'] == [[2, 10]]

        result = cdmi._get_cdmi_filters({'metadata:meta_prefix': None})
        assert len(result) == 1
        assert 'metadata' in result
        assert result['metadata'] == 'meta_prefix'

        result = cdmi._get_cdmi_filters({';parentURI': None})
        assert len(result) == 0

    def test_get_cdmi_filter_valid_multi(self):
        from eudat_http_api.http_storage import cdmi

        result = cdmi._get_cdmi_filters({'non_cdmi_argument': None,
                                         'objectType': None})
        assert len(result) == 1
        assert 'objectType' in result
        assert result['objectType'] is None

        result = cdmi._get_cdmi_filters({'objectId;objectName': None})
        assert len(result) == 2
        assert 'objectId' in result
        assert 'objectName' in result
        assert result['objectId'] is None
        assert result['objectName'] is None

        result = cdmi._get_cdmi_filters({'parentURI;parentID;': None})
        print result
        assert len(result) == 2
        assert 'parentURI' in result
        assert 'parentID' in result
        assert result['parentURI'] is None
        assert result['parentID'] is None

    def test_get_cdmi_filters_invalid(self):
        from eudat_http_api.http_storage import cdmi

        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'children:2e-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'children:2e3-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'children:-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'children:2-': None})

        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'value:2e-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'value:2e3-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'value:-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi._get_cdmi_filters, {'value:2-': None})

        # this doesn't even get recognized as cdmi argument
        #assert_raises(cdmi.MalformedArgumentValueException,
        #              cdmi._get_cdmi_filters, {';parentURI': None})

    def test_get_cdmi_json_generator_valid(self):
        from eudat_http_api.http_storage import cdmi

        def fake_gen():
            yield 'content'

        with patch('eudat_http_api.metadata.stat'), \
                patch('eudat_http_api.metadata.get_user_metadata'):
            result = cdmi._get_cdmi_json_generator('/home/test/',
                                                   'container',
                                                   dir_listing=[])

            result_list = list(result)
            for field in self.cdmi_container_mandatory_list:
                assert field in result_list

            result = cdmi._get_cdmi_json_generator('/home/test',
                                                   'object',
                                                   value_gen=fake_gen(),
                                                   file_size=7)

            result_list = list(result)
            for field in self.cdmi_object_mandatory_list:
                assert field in result_list
