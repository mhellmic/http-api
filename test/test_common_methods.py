import unittest
from eudat_http_api.common import ContentTypes


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

if __name__ == '__main__':
    unittest.main()
