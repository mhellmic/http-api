from Queue import Queue

import threading
import hashlib
from requests import get
import requests
from requests.auth import HTTPBasicAuth

from eudat_http_api.registration.models import db, RegistrationRequest
from eudat_http_api.epicclient import EpicClient, HTTPClient


def executor():
    while True:
        context = q.get()
        for step in workflow:
            print('Request id = %s advanced to = %s' %
                  (context.request_id, step.__name__))
            success = step(context)
            if not success:
                break
        q.task_done()


q = Queue()


def add_task(context):
    q.put(context)


def start_workers(num_worker_thread):
    for i in range(num_worker_thread):
        t = threading.Thread(target=executor)
        t.daemon = True
        t.start()


def update_status(context, status):
    r = RegistrationRequest.query.get(context.request_id)
    r.status_description = status
    db.session.add(r)
    db.session.commit()
    context.status = status


def check_src(context):
    update_status(context, 'Checking source')
    return check_url(context.src_url, context.auth)


def check_metadata(context):
    update_status(context, 'Checking metadata')
    return check_url(context.md_url, context.auth)


def check_url(url, auth):
    response = requests.head(url, auth=auth)
    if response.status_code != requests.codes.ok:
        return False

    return True


def copy_data_object(context):
    update_status(context, 'Copying data object to new location')
    destination = get_destination(context)
    print('Moving %s to %s' % (context.src_url, destination))

    context.destination = destination
    context.checksum = get_checksum(destination)
    return True


EPIC_URI = 'http://www'
EPIC_USER = 'user'
EPIC_PASS = 'pass'
EPIC_PREFIX = '666'


def get_epic_client():
    http_client = HTTPClient(EPIC_URI, HTTPBasicAuth(EPIC_USER, EPIC_PASS))
    return EpicClient(httpClient=http_client)


def get_handle(context):
    update_status(context, 'Creating handle')

    epic_client = get_epic_client()
    pid = epic_client.create_new(EPIC_PREFIX, context.location, context
                                 .checksum)
    context.pid = pid
    return True


def start_replication(context):
    update_status(context, 'Starting replication')
    return True


def get_checksum(destination):
    return 667


def download_to_file(url, destination):
    r = get(url, stream=True)
    with open(destination, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                f.flush()
    return True


def get_destination(self, source_url):
    return '%s%s' % (self.base_url, hashlib.sha256(source_url).hexdigest())


workflow = [check_src, check_metadata, copy_data_object, get_handle,
            start_replication]