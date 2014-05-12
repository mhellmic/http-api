import unittest
from eudat_http_api.common import ContentTypes, is_local


class TestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_content_type(self):
        json = ContentTypes.json
        json2 = ContentTypes.json
        cdmi_object = ContentTypes.cdmi_object
        assert json == json2
        assert json == json
        assert json != cdmi_object

        assert json == 'application/json'
        assert json2 == 'application/json'
        assert cdmi_object == 'application/cdmi-object'

    def test_is_local(self):
        url = 'irods://irods0-eudat.rzg.mpg.de:1247/vzRZGE/eudat/clarin/archive/qfs1/media-archive/file.txt'
        zone1 = 'vzRZGE'
        local_host = 'irods0-eudat.rzg.mpg.de'
        local_port = 1247
        res = is_local(url, local_host, local_port, zone1)
        assert res

        res = is_local(url, 'localhost', local_port, zone1)
        assert not res

        res = is_local(url, local_host, 661, zone1)
        assert not res

        res = is_local(url, local_host, local_port, 'tempZone')
        assert not res

        res = is_local(url, 'localhost', 1221, 'tempZone')
        assert not res

if __name__ == '__main__':
    unittest.main()
