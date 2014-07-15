from Queue import Queue

import threading
import hashlib
import requests
from requests.auth import HTTPBasicAuth

from eudat_http_api.cdmiclient import CDMIClient
from eudat_http_api.registration.models import db, RegistrationRequest
from eudat_http_api.epicclient import EpicClient, HandleRecord, \
    extract_prefix_suffix


def get_checksum(destination):
    return 667


config = dict()


def set_config(new_config):
    global config
    for k in new_config:
        config[k] = new_config[k]


def get_epic_client():
    return EpicClient(base_uri=config['HANDLE_URI'], credentials=HTTPBasicAuth(
        config['HANDLE_USER'], config['HANDLE_PASS']), debug=False)


def stream_download(source, file_handle, chunk_size=4194304):
    for chunk in source.iter_content(chunk_size=chunk_size):
        if chunk:
            file_handle.write(chunk)
            file_handle.flush()
    return True


def check_url(url, auth):
    response = requests.head(url, auth=auth, allow_redirects=True)
    if response.status_code != requests.codes.ok:
        return False

    return True


def extract_credentials(auth):
    """Extract credentials from request authentication object

    Only a place-holder currently.

    Works only with basic authentication so far. In the future I expect a
    change here. We will extract the target identity from the provided
    short-lived certificate and use chmod after the data object
    creation

    @param auth:
    @return: username, password
    """
    return auth.username, auth.password


def get_destination_url(context):
    """Returns the destination URL for the file.

    This has to be a working HTTP URL, since we access it through the
    HTTP interface.
    """
    return 'http://%s%s%s' % (
        config['HTTP_ENDPOINT'],
        config['IRODS_SAFE_STORAGE'],
        hashlib.sha256(context.src_url).hexdigest())


def get_replication_destination(context):
    """Returns the replication targets.

    This is an irods-internal value and should be removed at some point.
    """
    return '%s%s' % (config['IRODS_REPLICATION_DESTINATION'],
                     hashlib.sha256(context.src_url).hexdigest())


def get_replication_filename(context):
    return '%s%s.replicate' % (config['IRODS_SHARED_SPACE'], context.pid
                               .split('/')[-1])


def get_replication_command(context):
    # Format: '*pid;*source;*destination'
    return '%s;%s;%s' % (context.pid, context.destination, context
                         .replication_destination)


def create_storage_url(path):
    return 'irods://%s:%d%s' % (config['RODSHOST'], config['RODSPORT'],
                                path)


def check_src(context):
    update_request(context, 'Checking source')
    return check_url(context.src_url, context.auth)


def check_metadata(context):
    update_request(context, 'Checking metadata')
    return check_url(context.md_url, context.auth)


def copy_data_object(context):
    update_request(context, 'Copying data object to the new location')
    destination = get_destination_url(context)
    username, password = extract_credentials(context.auth)

    context.destination = destination
    # this is probably not the right place. the storage backend should
    # create a checksum if required. let's check if that is possible.
    context.checksum = get_checksum(destination)

    client = CDMIClient((username, password))

    upload_response = client.cdmi_copy(
        context.destination, context.src_url)
    if upload_response.status_code != 201:
        update_request(context, 'Unable to move the data to register space')
        return False

    return True


def get_handle(context):
    update_request(context, 'Creating handle')

    epic_client = get_epic_client()
    pid = epic_client.create_new(config['HANDLE_PREFIX'],
                                 HandleRecord.get_handle_with_values(
                                     create_storage_url(context.destination),
                                     context.checksum))
    if pid is None:
        return False

    context.pid = '/'.join(extract_prefix_suffix(pid))
    return True


def start_replication(context):
    update_request(context, 'Starting replication')
    context.replication_destination = get_replication_destination(context)

    # here we have to think about whether there will be a service account
    # starting the replication with the appropriate permissions.
    # b2safe description should give more information.
    username, password = extract_credentials(context.auth)

    client = CDMIClient((username, password))
    client.cdmi_put(get_replication_filename(context),
                    get_replication_command(context))

    return True


#execution-related stuff: workers, task queue & workflow definition


def update_request(context, status):
    r = RegistrationRequest.query.get(context.request_id)
    r.status_description = status
    print 'Request %d advanced to %s' % (r.id, status)
    #we could also add other properties from context to request (dst?)
    if hasattr(context, 'pid'):
        r.pid = context.pid

    db.session.add(r)
    db.session.commit()
    context.status = status


workflow = [check_src, check_metadata, copy_data_object, get_handle,
            start_replication]

q = Queue()


def add_task(context):
    q.put(context)


def executor():
    while True:
        context = q.get()
        success = False
        for step in workflow:
            print('Request id = %s advanced to = %s' %
                  (context.request_id, step.__name__))
            success = step(context)
            if not success:
                update_request(context, 'Failed during %s' % step.__name__)
                break

        if success:
            update_request(context, 'Request finished pid = %s ' % context.pid)
        q.task_done()


def start_workers(num_worker_thread):
    for i in range(num_worker_thread):
        t = threading.Thread(target=executor)
        t.daemon = True
        t.start()
