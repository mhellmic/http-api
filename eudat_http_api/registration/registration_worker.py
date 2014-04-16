# -*- coding: utf-8 -*-

from __future__ import with_statement

from base64 import b64decode
import threading
import time
import hashlib

from eudat_http_api.registration.models import RegistrationRequest

#jj: we probably want to move back to such a way of defining workflow
# (is more extensible)
# reply: What did you not like about having a list of functions
# that we call one after another?
# wf = [ check_source, upload, ... ]
# for func in wf:
#   func()
# or
# for func in wf:
#   try:
#       func()
#   except:
#       do_something()

workflow = ['check_source', 'upload', 'crate_handle']


class RegistrationWorker(threading.Thread):
    def __init__(self, request_id, epicclient, logger, cdmiclient, base_url,
                 db_session):
        threading.Thread.__init__(self)
        self.logger = logger
        self.request = RegistrationRequest.query.get(request_id)
        self.epicclient = epicclient
        self.cdmiclient = cdmiclient
        self.base_url = base_url
        self.destination = ''
        self.db_session = db_session

    def update_status(self, status, status_short=None):
        self.request.status = status_short
        if status is not None:
            self.request.status_description += ';'+status
        self.db_session.add(self.request)
        self.db_session.commit()

    def run(self):
        self.logger.debug('starting to process request with id = %s'
                          % self.request.id)
        self.continue_request(self.check_src)

    def check_src(self):
        self.update_status('Checking source')
        time.sleep(5)

        # check existence and correct permissions on source
        response = self.cdmiclient.cdmi_head('%s' % self.request.src_url)
        if response.status_code > 299:
            self.abort_request('Source is not available: %d'
                               % response.status_code)
            return
        else:
            self.logger.debug('Source exist')

        #check metadat will be moved in the future to become a separate
        #workflow step
        response = self.cdmiclient.cdmi_get('%s?%s' % (self.request.src_url,
                                                       'metadata'))
        metadata_json = response.json()
        self.logger.debug('metadata exist? %s' % metadata_json)

        self.continue_request(self.copy_data_object)

    def copy_data_object(self):
        self.update_status('Copying data object to new location')
        time.sleep(5)
        destination = self.get_destination(self.request.src_url)
        response = self.cdmiclient.cdmi_get(self.request.src_url)
        self.logger.debug('Moving %s to %s' % (self.request.src_url,
                                               destination))
        # cdmi_put is just a normal PUT!
        upload = self.cdmiclient.cdmi_put(
            destination, data=b64decode(response.json()['value']))
        if upload.status_code != 201:
            self.abort_request('Unable to move the data to register space')
            return

        self.destination = destination
        self.continue_request(self.get_handle)

    def get_handle(self):
        self.update_status('Creating handle')
        time.sleep(5)
        handle_key = "11007/00-ZZZZ-0000-0000-FAKE-7"

        self.update_status('Handle created: %s' % handle_key)

        handle = dict()
        handle['url'] = self.destination
        handle['checksum'] = 0
        handle['location'] = None

        self.request.pid = handle_key
        self.db_session.add(self.request)
        self.db_session.commit()

        self.logger.debug('Request %d finished' % self.request.id)
        self.update_status('Request finished', 'SUCCESS')

    def abort_request(self, reason_string):
        self.update_status(reason_string, 'FAIL')
        self.logger.error('Aborting request id = %s reason= %s'
                          % (self.request.id, reason_string))

    def continue_request(self, next_step):
        self.update_status(None, 'RUNNING')
        self.logger.debug('Request id = %s advanced to = %s'
                          % (self.request.id, next_step.__name__))
        #jj: not sure perhaps we could be more flexible with argument passing
        # (and require lambda or something?)
        #jj: we could also define the workflow in a more flexible way?
        next_step()

    def get_destination(self, source_url):
        return '%s%s' % (self.base_url, hashlib.sha256(source_url).hexdigest())
