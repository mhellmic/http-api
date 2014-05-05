from Queue import Queue

import threading
import hashlib
from requests import get
import requests
from requests.auth import HTTPBasicAuth

from eudat_http_api.registration.models import db, RegistrationRequest
from eudat_http_api.epicclient import EpicClient, HTTPClient
from irods import *


def check_url(url, auth):
    response = requests.head(url, auth=auth)
    if response.status_code != requests.codes.ok:
        return False

    return True


def get_checksum(destination):
    return 667


EPIC_URI = 'http://localhost:5000'
EPIC_USER = 'user'
EPIC_PASS = 'pass'
EPIC_PREFIX = '666'


def get_epic_client():
    http_client = HTTPClient(EPIC_URI, HTTPBasicAuth(EPIC_USER, EPIC_PASS))
    return EpicClient(http_client=http_client)


IRODS_HOST = 'localhost'
IRODS_PORT = 1247
IRODS_ZONE = 'tempZone'


def connect_to_irods(host, port, username, password, zone):
    conn, err = rcConnect(host, port, username, zone)
    if err.status != 0:
        print 'ERROR: Unable to connect to irods'
        return None

    if conn is None:
        return False

    err = clientLoginWithPassword(conn, password)
    if err != 0:
        return False

    print 'Connection successful'
    return conn


def get_irods_file_handle(connection, filename):
    fh = irodsOpen(connection, filename, mode='w')
    return fh


def stream_download(source, file_handle, chunk_size=4194304):
    for chunk in source.iter_content(chunk_size=chunk_size):
        if chunk:
            file_handle.write(chunk)
            file_handle.flush()
    return True


def check_url(url, auth):
    response = requests.head(url, auth=auth)
    if response.status_code != requests.codes.ok:
        return False

    return True


IRODS_SAFE_STORAGE = '/tempZone/safe/'


def get_destination(context):
    return '%s%s' % (IRODS_SAFE_STORAGE, hashlib.sha256(context.src_url)
                     .hexdigest())


def create_url(destination):
    return 'irods:/'+destination


def update_status(context, status):
    r = RegistrationRequest.query.get(context.request_id)
    r.status_description = status
    print 'Request %d advanced to %s' % (r.id, status)
    db.session.add(r)
    db.session.commit()
    context.status = status


def executor():
    while True:
        context = q.get()
        for step in workflow:
            print('Request id = %s advanced to = %s' %
                  (context.request_id, step.__name__))
            success = step(context)
            if not success:
                update_status(context, 'Failed during %s' % step.__name__)
                break

        if success:
            update_status(context, 'Request finished pid = %s ' % context.pid)
        q.task_done()


q = Queue()


def add_task(context):
    q.put(context)


def start_workers(num_worker_thread):
    for i in range(num_worker_thread):
        t = threading.Thread(target=executor)
        t.daemon = True
        t.start()


def check_src(context):
    update_status(context, 'Checking source')
    return check_url(context.src_url, context.auth)


def check_metadata(context):
    update_status(context, 'Checking metadata')
    return check_url(context.md_url, context.auth)


def extract_credentials(auth):
    #works only with basic auth so far but at least we have a placeholder
    return auth.username, auth.password


def copy_data_object(context):
    update_status(context, 'Copying data object to new location')
    destination = get_destination(context)
    username, password = extract_credentials(context.auth)
    conn = connect_to_irods(IRODS_HOST, IRODS_PORT, username, password,
                            IRODS_ZONE)
    fh = get_irods_file_handle(connection=conn, filename=destination)
    print 'Handle obtained '
    r = get(context.src_url, auth=context.auth, stream=True)
    stream_download(r, fh)
    fh.close()
    conn.disconnect()

    context.destination = destination
    context.checksum = get_checksum(destination)

    return True

def get_handle(context):
    update_status(context, 'Creating handle')

    epic_client = get_epic_client()
    pid = epic_client.create_new(EPIC_PREFIX, create_url(context
                                                         .destination), context
                                 .checksum)
    if pid is None:
        return False

    context.pid = pid
    return True


def start_replication(context):
    update_status(context, 'Starting replication')
    return True


workflow = [check_src, check_metadata, copy_data_object, get_handle,
            start_replication]



