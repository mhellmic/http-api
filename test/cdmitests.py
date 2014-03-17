from mock import patch
from nose.tools import assert_raises

from eudat_http_api import create_app


STORAGE = 'local'
DEBUG = True
TESTING = True


class TestCDMI:
    client = None

    def setup(self):

        app = create_app(__name__)
        self.client = app.test_client()

    def test_create_dirlist_dict_empty(self):
        from eudat_http_api.http_storage import cdmi

        with patch('eudat_http_api.metadata.stat'):
            result = cdmi.create_dirlist_dict([], '/home/')
            assert len(result) == 2
            assert result[0]['path'] == '/home/'
            assert result[0]['name'] == '.'
            assert result[1]['path'] == '/'
            assert result[1]['name'] == '..'

            result = cdmi.create_dirlist_dict([], '/home')
            assert len(result) == 2
            assert result[0]['path'] == '/home'
            assert result[0]['name'] == '.'
            assert result[1]['path'] == '/'
            assert result[1]['name'] == '..'

            result = cdmi.create_dirlist_dict([], '/')
            assert len(result) == 2
            assert result[0]['path'] == '/'
            assert result[0]['name'] == '.'
            assert result[1]['path'] == ''
            assert result[1]['name'] == '..'

    def test_create_dirlist_dict_one_dir(self):
        from eudat_http_api.http_storage import cdmi
        from eudat_http_api.http_storage import storage

        with patch('eudat_http_api.metadata.stat'):
            result = cdmi.create_dirlist_dict(
                [storage.StorageDir('test', '/home/test/')],
                '/home/')
            assert len(result) == 3
            assert result[0]['name'] == '.'
            assert result[1]['name'] == '..'
            assert result[2]['path'] == '/home/test/'
            assert result[2]['name'] == 'test'

            result = cdmi.create_dirlist_dict(
                [storage.StorageDir('test', '/home/test')],
                '/home/')
            assert len(result) == 3
            assert result[0]['name'] == '.'
            assert result[1]['name'] == '..'
            assert result[2]['path'] == '/home/test'
            assert result[2]['name'] == 'test'

    def test_create_dirlist_dict_one_file(self):
        from eudat_http_api.http_storage import cdmi
        from eudat_http_api.http_storage import storage

        with patch('eudat_http_api.metadata.stat'):
            result = cdmi.create_dirlist_dict(
                [storage.StorageDir('test', '/home/test')],
                '/home/')
            assert len(result) == 3
            assert result[0]['name'] == '.'
            assert result[1]['name'] == '..'
            assert result[2]['path'] == '/home/test'
            assert result[2]['name'] == 'test'

    def test_get_cdmi_filters_valid_single(self):
        from eudat_http_api.http_storage import cdmi

        result = cdmi.get_cdmi_filters({})
        assert result == {}

        result = cdmi.get_cdmi_filters({'non_cdmi_argument': None})
        assert result == {}

        result = cdmi.get_cdmi_filters({'children:2-10': None})
        assert len(result) == 2
        assert 'children' in result
        assert 'childrenrange' in result
        assert result['children'] == [2, 10]
        assert result['childrenrange'] == [2, 10]

        result = cdmi.get_cdmi_filters({'value:2-10': None})
        assert len(result) == 1
        assert 'value' in result
        assert result['value'] == [[2, 10]]

    def test_get_cdmi_filter_valid_multi(self):
        from eudat_http_api.http_storage import cdmi

        result = cdmi.get_cdmi_filters({'non_cdmi_argument': None,
                                        'objectType': None})
        assert len(result) == 1
        assert 'objectType' in result
        assert result['objectType'] is None

        result = cdmi.get_cdmi_filters({'objectId;objectName': None})
        assert len(result) == 2
        assert 'objectId' in result
        assert 'objectName' in result
        assert result['objectId'] is None
        assert result['objectName'] is None

        result = cdmi.get_cdmi_filters({'parentURI;parentID;': None})
        print result
        assert len(result) == 2
        assert 'parentURI' in result
        assert 'parentID' in result
        assert result['parentURI'] is None
        assert result['parentID'] is None

    def test_get_cdmi_filters_invalid(self):
        from eudat_http_api.http_storage import cdmi

        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'children:2e-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'children:2e3-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'children:-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'children:2-': None})

        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'value:2e-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'value:2e3-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'value:-10': None})
        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {'value:2-': None})

        assert_raises(cdmi.MalformedArgumentValueException,
                      cdmi.get_cdmi_filters, {';parentURI': None})


#def test_get_cdmi_json_file_generator_valid():
#    def fake_value_gen():
#        yield 'content'
#
#    with patch('metadata.stat'), \
#            patch('metadata.get_user_metadata'):
#                result = cdmi.get_cdmi_json_file_generator('/home/test',
#                                                           fake_value_gen(),
#                                                           7)
