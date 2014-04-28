
import unittest
from datetime import datetime

from eudat_http_api.registration.models import RegistrationRequest
from eudat_http_api.registration.registration_worker import RegistrationWorker


class TestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    class DummyLogger:
        def debug(self, message):
            print 'Debug %s' % message

        def error(self, message):
            print 'Error %s' % message

    def test_workflow(self):
        print 'Starting thread'
        r = RegistrationRequest(id=666, src_url='some url', status_description='W', timestamp=datetime.utcnow())
        # start worker
        p = RegistrationWorker(request_id=666, epic_client=None, logger=None, cdmi_client=None, base_url='');
        p.start()
        p.join()
