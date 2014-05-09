import unittest
from eudat_http_api.epicclient import HandleRecord


class TestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_add_url(self):
        expected_result = 'http://www.google.com'
        h = HandleRecord()
        h.add_url(expected_result)
        res = h.get_url_value()
        assert res == expected_result

    def test_add_checksum(self):
        h = HandleRecord()
        h.add_checksum(6673)
        res = h.get_checksum_value()
        assert res == 6673

    def test_get_url_value(self):
        h = HandleRecord()
        res = h.get_url_value()
        assert res is None
        h.add_url('http://www.foo.bar/')
        assert 'http://www.foo.bar/' == h.get_url_value()
        assert 'http://www.rando.m/' != h.get_url_value()

    def test_get_checksum(self):
        h = HandleRecord()
        res = h.get_checksum_value()
        assert res is None
        h.add_checksum(1234)
        assert 1234 == h.get_checksum_value()
        assert 7631 != h.get_checksum_value()

    def test_handle_factory_method(self):
        h = HandleRecord.get_handle_with_values('http://www.foo.bar')
        assert h is not None
        assert 'http://www.foo.bar' == h.get_url_value()
        assert h.get_checksum_value() is None

    def test_handle_factory_method_with_checksum(self):
        h = HandleRecord.get_handle_with_values('http://www.foo.bar', 667)
        assert h is not None
        assert 'http://www.foo.bar' == h.get_url_value()
        assert h.get_checksum_value() is not None
        assert 667 == h.get_checksum_value()


if __name__ == '__main__':
    unittest.main()
