import re
import tempfile

from test.test_common import TestApi
from test.test_common import ByteRange


DB_FD, DB_FILENAME = tempfile.mkstemp()
SQLALCHEMY_DATABASE_URI = '%s%s' % ('sqlite:///', DB_FILENAME)
DEBUG = True
TESTING = True
STORAGE = 'local'


class TestHttpApi(TestApi):

    def assert_html_response(self, rv):
        assert rv.content_type.startswith('text/html')
        assert rv.mimetype == 'text/html'

    def test_html_get(self):
        for t in self.check_resource(self.check_html_get):
            yield t

    def test_html_put(self):
        for t in self.check_resource(self.check_html_put):
            yield t

    def test_html_del(self):
        for t in self.check_resource(self.check_html_del):
            yield t

    def check_html_get(self, params):
        if params['resource'].is_dir() and params['resource'].exists:
            self.check_html_folder_get(**params)
        elif params['resource'].is_dir() and not params['resource'].exists:
            self.check_html_folder_get_404(**params)
        elif params['resource'].is_file() and params['resource'].exists:
            self.check_html_file_get(**params)
            self.check_html_file_get_partial(**params)
        elif params['resource'].is_file() and not params['resource'].exists:
            self.check_html_file_get_404(**params)

    def check_html_put(self, params):
        if params['resource'].is_dir():
            self.check_html_folder_put(**params)
        elif params['resource'].is_file():
            self.check_html_file_put(**params)

    def check_html_del(self, params):
        if params['resource'].is_file():
            self.check_html_file_del(**params)
        elif params['resource'].is_dir() and params['resource'].exists:
            self.check_html_folder_del(**params)
        elif params['resource'].is_dir() and not params['resource'].exists:
            self.check_html_folder_del_404(**params)

    def check_html_folder_get(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if url[-1] != '/':
            assert rv.status_code == 302
            assert rv.headers.get('Location') == 'http://localhost%s/' % url
            self.assert_html_response(rv)
        else:
            assert rv.status_code == 200
            self.assert_html_response(rv)
            # check that there is a list
            assert re.search('<ul.*>.*(<li>.*</li>.*)*.*</ul>',
                             rv.data, re.DOTALL) is not None

    def check_html_folder_get_404(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_get(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 200
        self.assert_html_response(rv)

        assert rv.content_length == resource.objinfo['size']
        assert rv.data == resource.objinfo['content']

    def check_html_file_get_partial(self, resource, userinfo):
        obj_size = len(resource.objinfo['content'])

        byte_range = ByteRange(5, 10)
        headers = {'range': 'bytes=%s-%s' % (str(byte_range.start),
                                             str(byte_range.end)
                                             )}
        rv = self.open_with_auth(resource.path, 'GET',
                                 userinfo.name, userinfo.password,
                                 headers=headers)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 206
        self.assert_html_response(rv)

        if obj_size > byte_range.end:
            assert rv.content_length == len(byte_range)
        assert rv.data == (resource.objinfo['content']
                           [byte_range.start:byte_range.end + 1])

        # leave out first part: expect fileend - end bytes
        byte_range = ByteRange(obj_size - 6, obj_size)
        headers = {'range': 'bytes=%s-%s' % ('',
                                             str(6)
                                             )}
        rv = self.open_with_auth(resource.path, 'GET',
                                 userinfo.name, userinfo.password,
                                 headers=headers)

        if obj_size > 6:
            assert rv.status_code == 206
        else:
            # now you got served the whole file
            assert rv.status_code == 200
        self.assert_html_response(rv)

        assert rv.data == (resource.objinfo['content']
                           [byte_range.start:byte_range.end + 1])

        # leave out last part: request to file end
        byte_range = ByteRange(2, obj_size)
        headers = {'range': 'bytes=%s-%s' % (str(byte_range.start),
                                             ''
                                             )}
        rv = self.open_with_auth(resource.path, 'GET',
                                 userinfo.name, userinfo.password,
                                 headers=headers)

        assert rv.status_code == 206
        self.assert_html_response(rv)

        if obj_size > byte_range.end:
            assert rv.content_length == len(byte_range) - 1
        assert rv.data == (resource.objinfo['content']
                           [byte_range.start:byte_range.end + 1])

        # use invalid range identifiers
        byte_range = ByteRange(2, obj_size)
        headers = {'range': 'bytes=%s-%s' % (str(byte_range.start)+'ef',
                                             'beefsteak'
                                             )}
        rv = self.open_with_auth(resource.path, 'GET',
                                 userinfo.name, userinfo.password,
                                 headers=headers)

        assert rv.status_code == 400
        self.assert_html_response(rv)

    def check_html_file_get_404(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'GET',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_del(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'DELETE',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if resource.exists:
            assert rv.status_code == 204
        else:
            assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_folder_del(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'DELETE',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if (resource.objtype == resource.ContainerType and
                url[-1] != '/'):
            assert (rv.headers.get('Location') ==
                    'http://localhost%s/' % url)
        elif (resource.objtype == resource.ContainerType and
                resource.objinfo['children'] == 0):
            assert rv.status_code == 204
        elif (resource.objtype == resource.ContainerType and
                resource.objinfo['children'] > 0):
            assert rv.status_code == 409
        elif resource.objtype == resource.FileType:
            assert rv.status_code == 204

        self.assert_html_response(rv)

    def check_html_folder_del_404(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'DELETE',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        assert rv.status_code == 404
        self.assert_html_response(rv)

    def check_html_file_put(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'PUT',
                                 userinfo.name, userinfo.password,
                                 data=resource.objinfo['content'])

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if resource.exists:
            assert rv.status_code == 409
        elif not resource.parent_exists:
            assert rv.status_code == 404
        else:
            assert rv.status_code == 201
        self.assert_html_response(rv)

    def check_html_folder_put(self, resource, userinfo):
        url = resource.path
        rv = self.open_with_auth(url, 'PUT',
                                 userinfo.name, userinfo.password)

        if not userinfo.valid:
            assert rv.status_code == 401
            return

        if resource.exists:
            assert rv.status_code == 409
        elif not resource.parent_exists:
            assert rv.status_code == 404
        else:
            assert rv.status_code == 201
        self.assert_html_response(rv)
