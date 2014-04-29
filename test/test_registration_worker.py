import os
import unittest
from datetime import datetime

from eudat_http_api.registration.models import RegistrationRequest
from eudat_http_api.registration.registration_worker import RegistrationWorker
from eudat_http_api import create_app
from eudat_http_api.registration.models import db


class DummyLogger:
        def debug(self, message):
            print 'Debug %s' % message

        def error(self, message):
            print 'Error %s' % message


class TestCase(unittest.TestCase):
    def setUp(self):
        app = create_app('test_config')
        self.app = app
        self.client = app.test_client()

        db.create_all()

    def tearDown(self):
        db.drop_all()
        os.remove(self.app.config['DB_FILENAME'])

    def test_workflow(self):
        print 'Starting thread'
        r = RegistrationRequest(src_url='http://www.foo.bar/',
                                status_description='Registration request '
                                                   'created',
                                timestamp=datetime.utcnow())
        db.session.add(r)
        db.session.commit()
        logger = DummyLogger()
        # start worker
        p = RegistrationWorker(request_id=r.id,
                               epic_client=None,
                               logger=logger,
                               cdmi_client=None,
                               base_url='http://www.goo.bar/')
        db.session.close()
        p.start()
        p.join()
