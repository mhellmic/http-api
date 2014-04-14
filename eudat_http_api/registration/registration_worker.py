# -*- coding: utf-8 -*-

from __future__ import with_statement

import json
import threading

import time
from eudat_http_api import cdmiclient

from eudat_http_api.registration.models import db, RegistrationRequest


request_statuses = {
    'waiting to be started': 'W',
    'started': 'S',
    'src checked': 'E',
    'dst permissions checked': 'DP',
    'checksums in request and src match': 'C',
    'retrieved PID': 'P',
    'file copied to dst space': 'FC',
    'aborted': 'A'
}

class RegistrationWorker(threading.Thread):

    def __init__(self, request_id, epicclient, logger):
        threading.Thread.__init__(self)
        self.logger = logger
        self.request = RegistrationRequest.query.get(request_id)
        self.epicclient = epicclient
        self.logger.debug("DB Current app in thread %s " % db.get_app())

    def run(self):
        self.logger.debug('starting to process request with id = %s' % self.request.id)
        self.continue_request(self.create_dst_url)


    def create_dst_url(self):
        self.request.status_description = 'Creating destination URL'
        db.session.add(self.request)
        db.session.commit()
        time.sleep(5)
        self.continue_request(self.check_src)


    def check_src(self):
        self.request.status_description = 'Checking source'
        db.session.add(self.request)
        db.session.commit()
        time.sleep(5)
        self.continue_request(self.get_handle)
        if 1==1:
            return

        # check existence and correct permissions on source
        _, response = cdmiclient.head('%s' % self.request.src_url)
        if response.status_code > 299:
            self.abort_request('Source file is not available')
        else:
            self.continue_request(self.get_handle)

        metadata, response = cdmiclient.cdmi_get('%s?%s' % (self.request.src_url, 'metadata'))
        metadata_json = json.loads(metadata.read())

        # also check the content of metadata; if it conforms to datacite3

        # we could use the request object as a store going from function to function,
        # so we can separate e.g. check_src_permissions and check_checksum,
        # but still do only one request
        # check existence and correct permissions on dsts
        metadata, response = cdmiclient.get('%s?%s' % (self.request['dst_url'], 'metadata'))
        if response.status_code > 299:
            self.abort_request('Dst location is not available')
        else:
            self.continue_request(self.get_handle)


    def get_handle(self):
        self.request.status_description = 'Getting handle'
        db.session.commit()
        time.sleep(5)
        self.continue_request(self.copy_data_object)


    def copy_data_object(self):
        self.request.status_description = 'Registration completed'
        db.session.commit()
        time.sleep(5)
        self.logger.debug('Request finished id = %s' % self.request.id)


    def abort_request(self, reason_string):
        self.logger.error('Aborting request id = %s reason= %s' % (self.request.id, reason_string))


    def continue_request(self, next_step):
        self.logger.debug('Request id = %s advanced to = %s' % (self.request.id, next_step.__name__))
        #jj: not sure perhaps we could be more flexible with argument passing (and require lambda or something?)
        #jj: we could also define the workflow in a more flexible way?
        next_step()
