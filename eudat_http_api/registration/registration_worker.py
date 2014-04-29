from __future__ import with_statement

import threading
import hashlib

from eudat_http_api.registration.models import db, RegistrationRequest

#jj: we probably want to move back to such a way of defining workflow
workflow = ['check_source', 'upload', 'crate_handle']


class RegistrationWorker(threading.Thread):
    def __init__(self, request_id, epic_client, logger, cdmi_client, base_url):
        threading.Thread.__init__(self)
        self.logger = logger
        self.request = RegistrationRequest.query.get(request_id)
        self.epic_client = epic_client
        self.cdmi_client = cdmi_client
        self.base_url = base_url
        self.destination = ''

    def update_status(self, status):
        self.request.status_description = status
        db.session.add(self.request)
        db.session.commit()

    def run(self):
        self.logger.debug('starting to process request with id = %s'
                          % self.request.id)
        self.continue_request(self.check_src)

    def check_src(self):
        self.update_status('Checking source')
        # check existence and correct permissions on source
        response = self.cdmi_client.cdmi_head('%s' % self.request.src_url)
        if response.status_code > 299:
            self.abort_request(
                'Source is not available: %d' % response.status_code)
            return
        else:
            self.logger.debug('Source exist')

        # metadata check can become a separate workflow step
        response = self.cdmi_client.cdmi_get(
            '%s?%s' % (self.request.src_url, 'metadata'))
        metadata_json = response.json()
        self.logger.debug('metadata exist? %s' % metadata_json)

        self.continue_request(self.copy_data_object)

    def copy_data_object(self):
        self.update_status('Copying data object to new location')
        destination = self.get_destination(self.request.src_url)
        response = self.cdmi_client.cdmi_get(self.request.src_url)
        self.logger.debug(
            'Moving %s to %s' % (self.request.src_url, destination))
        upload = self.cdmi_client.cdmi_put(destination,
                                           data=response.json()['value'])
        if upload.status_code != 201:
            self.abort_request('Unable to move the data to register space')
            return

        self.destination = destination
        self.continue_request(self.get_handle)

    def get_handle(self):
        self.update_status('Creating handle')

        handle = dict()
        handle['url'] = self.destination
        handle['checksum'] = 0
        handle['location'] = None

        self.logger.debug('Request %d finished' % self.request.id)
        self.update_status('Request finished check %s' % self.destination)

    def abort_request(self, reason_string):
        self.logger.error('Aborting request id = %s reason= %s' % (
            self.request.id, reason_string))

    def continue_request(self, next_step):
        self.logger.debug('Request id = %s advanced to = %s' % (
            self.request.id, next_step.__name__))
        next_step()

    def get_destination(self, source_url):
        return '%s%s' % (self.base_url, hashlib.sha256(source_url).hexdigest())
