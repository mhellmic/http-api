import json
import unittest
from eudat_http_api.epicclient import HandleRecord


class TestCase(unittest.TestCase):

    epic_str = '[{"idx":1,"type":"URL",' \
                  '"parsed_data":"irods://irods0-eudat.rzg.mpg.de:1247/vzRZGE/eudat/clarin/archive/qfs1/media-archive/lac_data/Ozyurek//20100203172555.imdi","data":"aXJvZHM6Ly9pcm9kczAtZXVkYXQucnpnLm1wZy5kZToxMjQ3L3Z6UlpHRS9l\\ndWRhdC9jbGFyaW4vYXJjaGl2ZS9xZnMxL21lZGlhLWFyY2hpdmUvbGFjX2Rh\\ndGEvT3p5dXJlay9UdXJraXNoX1NpZ25fTGFuZ3VhZ2Uvc3lsdmVzdGVyX3R3\\nZWV0eS9DUl9WSURJX2RhdGEvQ1I1L01ldGFkYXRhLzIwMTAwMjAzMTcyNTU1\\nLmltZGk=","timestamp":"2013-10-24T12:30:03Z","ttl_type":0,"ttl":86400,"refs":[],"privs":"rwr-"},{"idx":2,"type":"10320/LOC","parsed_data":"<locations><location href=\\"irods://irods0-eudat.rzg.mpg.de:1247/vzRZGE/eudat/clarin/archive/qfs1/media-archive/lac_data/Ozyurek/Turkish_Sign_Language/sylvester_tweety/CR_VIDI_data/CR5/Metadata/20100203172555.imdi\\" id=\\"0\\"/><location href=\\"http://hdl.handle.net/11112/9d3fde44-adf4-11e3-8886-a0369f0b5f26\\" id=\\"1\\"/></locations>","data":"PGxvY2F0aW9ucz48bG9jYXRpb24gaHJlZj0iaXJvZHM6Ly9pcm9kczAtZXVk\\nYXQucnpnLm1wZy5kZToxMjQ3L3Z6UlpHRS9ldWRhdC9jbGFyaW4vYXJjaGl2\\nZS9xZnMxL21lZGlhLWFyY2hpdmUvbGFjX2RhdGEvT3p5dXJlay9UdXJraXNo\\nX1NpZ25fTGFuZ3VhZ2Uvc3lsdmVzdGVyX3R3ZWV0eS9DUl9WSURJX2RhdGEv\\nQ1I1L01ldGFkYXRhLzIwMTAwMjAzMTcyNTU1LmltZGkiIGlkPSIwIi8+PGxv\\nY2F0aW9uIGhyZWY9Imh0dHA6Ly9oZGwuaGFuZGxlLm5ldC8xMTExMi85ZDNm\\nZGU0NC1hZGY0LTExZTMtODg4Ni1hMDM2OWYwYjVmMjYiIGlkPSIxIi8+PC9s\\nb2NhdGlvbnM+","timestamp":"2014-03-17T16:54:24Z","ttl_type":0,"ttl":86400,"refs":[],"privs":"rwr-"},{"idx":3,"type":"CHECKSUM","parsed_data":"409b793ccab2c3b7113da1c8f8c1e5e5","data":"NDA5Yjc5M2NjYWIyYzNiNzExM2RhMWM4ZjhjMWU1ZTU=","timestamp":"2013-10-24T12:30:05Z","ttl_type":0,"ttl":86400,"refs":[],"privs":"rwr-"},{"idx":4,"type":"ROR","parsed_data":"http://hdl.handle.net/1839/00-0000-0000-000F-5A78-D","data":"aHR0cDovL2hkbC5oYW5kbGUubmV0LzE4MzkvMDAtMDAwMC0wMDAwLTAwMEYt\\nNUE3OC1E","timestamp":"2013-10-24T12:30:06Z","ttl_type":0,"ttl":86400,"refs":[],"privs":"rwr-"},{"idx":100,"type":"HS_ADMIN","parsed_data":{"adminId":"0.NA/11096","adminIdIndex":200,"perms":{"add_handle":true,"delete_handle":true,"add_naming_auth":false,"delete_naming_auth":false,"modify_value":true,"remove_value":true,"add_value":true,"read_value":true,"modify_admin":true,"remove_admin":true,"add_admin":true,"list_handles":false}},"data":"B/MAAAAKMC5OQS8xMTA5NgAAAMgAAA==","timestamp":"2013-10-24T12:30:03Z","ttl_type":0,"ttl":86400,"refs":[],"privs":"rwr-"}]'

    handle_str = '{"responseCode":1,"handle":"11113/dda2224c-16ca-11e3-bec5-005056be76d0","values":[{"index":1,"type":"URL","data":"irods://ed-res-01.csc.fi:1247/ed-csc/rc/enes/cmip5/output1/MPI-M/MPI-ESM-LR/rcp45/mon/ocean/Omon/r1i1p1/v20120110/hfsithermds/hfsithermds_Omon_MPI-ESM-LR_rcp45_r1i1p1_229001-230012.nc","ttl":86400,"timestamp":"2013-09-06T08:03:51Z"},{"index":2,"type":"10320/LOC","data":"<locations><location id=\\"0\\" href=\\"irods://ed-res-01.csc.fi:1247/ed-csc/rc/enes/cmip5/output1/MPI-M/MPI-ESM-LR/rcp45/mon/ocean/Omon/r1i1p1/v20120110/hfsithermds/hfsithermds_Omon_MPI-ESM-LR_rcp45_r1i1p1_229001-230012.nc\\" /></locations>","ttl":86400,"timestamp":"2013-09-06T08:03:51Z"},{"index":3,"type":"CHECKSUM","data":"393e2b4fad2df7e30c89d6287969d0b1","ttl":86400,"timestamp":"2013-09-06T08:03:53Z"},{"index":4,"type":"ROR","data":"http://hdl.handle.net/11098/e63ded44-ca6e-11e2-886a-5a4013fedfa4","ttl":86400,"timestamp":"2013-09-06T08:03:55Z"},{"index":100,"type":"HS_ADMIN","data":{"format":"admin","value":{"handle":"0.NA/11113","index":200,"permissions":"011111110011"}},"ttl":86400,"timestamp":"2013-09-06T08:03:51Z"}]}'



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

    def test_to_json_array(self):
        h = HandleRecord.get_handle_with_values('http://www.foo.bar', 634)
        json_str = h.to_epic_json_array()
        assert json_str is not None
        assert json_str.count('http://www.foo.bar') == 1
        array = json.loads(json_str)
        array.sort()
        assert array[0]['parsed_data'] == 634
        assert array[1]['parsed_data'] == 'http://www.foo.bar'

    def test_from_epic_json_array(self):
        h = HandleRecord.from_json(json.loads(self.epic_str))
        assert h is not None
        assert h.get_url_value() == 'irods://irods0-eudat.rzg.mpg' \
                                   '.de:1247/vzRZGE/eudat/clarin/archive/qfs1/media-archive/lac_data/Ozyurek//20100203172555.imdi'
        assert h.get_checksum_value() == '409b793ccab2c3b7113da1c8f8c1e5e5'


    def test_from_handle_json_array(self):
        h = HandleRecord.from_json(json.loads(self.handle_str))
        assert h is not None
        assert h.get_url_value() == 'irods://ed-res-01.csc.fi:1247/ed-csc/rc/enes/cmip5/output1/MPI-M/MPI-ESM-LR/rcp45/mon/ocean/Omon/r1i1p1/v20120110/hfsithermds/hfsithermds_Omon_MPI-ESM-LR_rcp45_r1i1p1_229001-230012.nc'
        assert h.get_checksum_value() == '393e2b4fad2df7e30c89d6287969d0b1'

    def test_to_string(self):
        h = HandleRecord.get_handle_with_values('http://www.foo.bar', 772)
        print h

if __name__ == '__main__':
    unittest.main()
