import unittest
from eudat_http_api.common import ContentTypes


class TestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ContentType(self):
        json = ContentTypes.json
        json2 = ContentTypes.json
        cdmiObject = ContentTypes.cdmi_object
        assert json == json2
        assert json == json
        assert json != cdmiObject

        assert json == "application/json"
        assert json2 == "application/json"
        assert cdmiObject == "application/cdmi-object"

