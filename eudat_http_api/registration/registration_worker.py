# -*- coding: utf-8 -*-

from __future__ import with_statement

import json
import threading

import time
from requests.auth import HTTPBasicAuth
from eudat_http_api import cdmiclient

from eudat_http_api.registration.models import db, RegistrationRequest


workflow = ['check_source', 'upload', 'crate_handle']


class RegistrationWorker(threading.Thread):
    def __init__(self, request_id, epicclient, logger, auth):
        threading.Thread.__init__(self)
        self.logger = logger
        self.request = RegistrationRequest.query.get(request_id)
        self.epicclient = epicclient
        self.auth = auth
        self.logger.debug("DB Current app in thread %s " % db.get_app())

    def update_status(self, status):
        self.request.status_description = status
        db.session.add(self.request)
        db.session.commit()

    def run(self):
        self.logger.debug('starting to process request with id = %s' % self.request.id)
        self.continue_request(self.check_src)

    def check_src(self):
        self.update_status('Checking source')
        time.sleep(5)
        self.continue_request(self.copy_data_object)

        # check existence and correct permissions on source
        response = cdmiclient.head('%s' % self.request.src_url,
                                      auth=HTTPBasicAuth(self.auth.username, self.auth.password))
        if response.status_code > 299:
            self.abort_request('Source is not available: %d' % response.status_code)
        else:
            self.logger.debug('Source exist')

        #check metadat will be moved in the future to become a separate workflow step
        metadata, response = cdmiclient.cdmi_get('%s?%s' % (self.request.src_url, 'metadata'))
        metadata_json = json.loads(metadata.read())
        self.logger.debug('metadata exist? %s' % metadata_json)

        self.continue_request(self.get_handle)


    def copy_data_object(self):
        self.update_status('Copying data object to new location')
        time.sleep(5)
        self.destination_directory = self.get_destination(self.request.src_url)
        self.continue_request(self.get_handle)

    def get_handle(self):
        self.update_status('Creating handle')
        time.sleep(5)
        self.logger.debug('Request %d finished' % self.request.id)

    def abort_request(self, reason_string):
        self.logger.error('Aborting request id = %s reason= %s' % (self.request.id, reason_string))


    def continue_request(self, next_step):
        self.logger.debug('Request id = %s advanced to = %s' % (self.request.id, next_step.__name__))
        #jj: not sure perhaps we could be more flexible with argument passing (and require lambda or something?)
        #jj: we could also define the workflow in a more flexible way?
        next_step()

    def get_destination(self, source_url):
        pass