from Queue import Queue

import threading
import hashlib
from requests import get
import requests
from requests.auth import HTTPBasicAuth

from eudat_http_api.registration.models import db, RegistrationRequest
from eudat_http_api.epicclient import EpicClient, HTTPClient
from irods import rcConnect, clientLoginWithPassword, irodsOpen


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
# final destination of the files (local safe storage)
IRODS_SAFE_STORAGE = '/%s/safe/' % IRODS_ZONE
# where the replication commands are written
IRODS_SHARED_SPACE = '/%s/replicate/' % IRODS_ZONE
# in the process of replication you have to define the destination where the
#  data will be stored (for test local zone is ok). HTTP does not write to
# this location this is done by replication rules.
IRODS_REPLICATION_DESTINATION = '/%s/replicated/' % IRODS_ZONE


def connect_to_irods(host, port, username, password, zone):
    conn, err = rcConnect(host, port, username, zone)
    if err.status != 0:
        print 'ERROR: Unable to connect to iRODS@%s' % IRODS_HOST
        return None

    if conn is None:
        return conn

    err = clientLoginWithPassword(conn, password)
    if err != 0:
        return conn

    print 'Connection successful'
    return conn


def get_irods_file_handle(connection, filename):
    return irodsOpen(connection, filename, mode='w')


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


def get_destination(context):
    return '%s%s' % (IRODS_SAFE_STORAGE, hashlib.sha256(context.src_url)
                     .hexdigest())


def get_replication_destination(context):
    return '%s%s' % (IRODS_REPLICATION_DESTINATION,
                     hashlib.sha256(context.src_url).hexdigest())


def get_replication_filename(context):
    return '%s%s.replicate' % (IRODS_SHARED_SPACE, context.pid.split('/')[-1])


def get_replication_command(context):
    # Format: '*pid;*source;*destination'
    return '%s;%s;%s' % (context.pid, context.destination, context
                         .replication_destination)


def create_url(destination):
    return 'irods:/'+destination


def update_status(context, status):
    r = RegistrationRequest.query.get(context.request_id)
    r.status_description = status
    print 'Request %d advanced to %s' % (r.id, status)
    db.session.add(r)
    db.session.commit()
    context.status = status


def check_src(context):
    update_status(context, 'Checking source')
    return check_url(context.src_url, context.auth)


def check_metadata(context):
    update_status(context, 'Checking metadata')
    return check_url(context.md_url, context.auth)


def extract_credentials(auth):
    """Extract irods credentials from request authentication object

    Only a place-holder currently.

    Works only with basic authentication so far. In the future I expect a
    change here. We will extract the target identity from the provided
    short-lived certificate and use irods.chmode after the data object
    creation

    @param auth:
    @return: username, password that can be used in irods.
    """
    return auth.username, auth.password


def copy_data_object(context):
    update_status(context, 'Copying data object to the new location')
    destination = get_destination(context)
    username, password = extract_credentials(context.auth)
    conn = connect_to_irods(IRODS_HOST, IRODS_PORT, username, password,
                            IRODS_ZONE)
    target = get_irods_file_handle(connection=conn, filename=destination)
    source = get(url=context.src_url, auth=context.auth, stream=True)
    stream_download(source, target)
    target.close()
    conn.disconnect()

    context.destination = destination
    context.checksum = get_checksum(destination)

    return True


def get_handle(context):
    update_status(context, 'Creating handle')

    epic_client = get_epic_client()
    pid = epic_client.create_new(EPIC_PREFIX, create_url(context.destination),
                                 context.checksum)
    if pid is None:
        return False

    context.pid = pid
    return True


def start_replication(context):
    update_status(context, 'Starting replication')
    context.replication_destination = get_replication_destination(context)

    username, password = extract_credentials(context.auth)
    conn = connect_to_irods(IRODS_HOST, IRODS_PORT, username, password,
                            IRODS_ZONE)
    target = get_irods_file_handle(
        connection=conn,
        filename=get_replication_filename(context))

    replication_command = get_replication_command(context)

    target.write(replication_command)
    target.close()
    conn.close()

    return True

#execution-related stuff: workers, task queue & workflow definition


workflow = [check_src, check_metadata, copy_data_object, get_handle,
            start_replication]

q = Queue()


def add_task(context):
    q.put(context)


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


def start_workers(num_worker_thread):
    for i in range(num_worker_thread):
        t = threading.Thread(target=executor)
        t.daemon = True
        t.start()



