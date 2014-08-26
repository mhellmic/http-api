from flask import Blueprint
import flask
from flask import current_app
from flask import request
from flask import json
from flask import abort, url_for
from flask.ext.login import login_required
from werkzeug.utils import redirect

from eudat_http_api.common import request_wants, ContentTypes, is_local
from eudat_http_api.epicclient import EpicClient

from eudat_http_api.registration.models import db, RegistrationRequest, \
    RegistrationRequestSerializer
from eudat_http_api.registration.registration_worker import add_task, \
    start_workers, set_config

from datetime import datetime
from requests.auth import HTTPBasicAuth

registration = Blueprint('registration', __name__,
                         template_folder='templates')


class Context():
    pass


def get_hal_links(reg_requests, page):
    """returns links in json hal format"""
    navi = dict()
    navi['self'] = {'href': url_for('.get_requests', page=page)}
    if reg_requests.has_next:
        navi['next'] = {
            'href': url_for('.get_requests', page=reg_requests.next_num)}
    if reg_requests.has_prev:
        navi['prev'] = {
            'href': url_for('.get_requests', page=reg_requests.prev_num)}

    return navi


@registration.route('/request/', methods=['GET'])
@login_required
def get_requests():
    """Get a requests list."""
    page = int(request.args.get('page', '1'))
    reg_requests = RegistrationRequest.query.order_by(
        RegistrationRequest.timestamp.desc()).paginate(page,
                                                       current_app.config[
                                                           'REQUESTS_PER_PAGE'],
                                                       False)

    if request_wants(ContentTypes.json):
        return flask.jsonify(
            {"requests": RegistrationRequestSerializer(reg_requests.items,
                                                       many=True).data,
             "_links": get_hal_links(reg_requests, page)})

    src = request.args.get('src', '')
    return flask.render_template(
        'requests.html',
        scratch=current_app.config.get('SCRATCH_SPACE', None),
        requests=reg_requests,
        src=src)


def extract_urls(url):
    """Extract data and metadata urls from cdmi url

    The source URL should have no query string attached,
    so we can also get it over plain HTTP and not in the
    CDMI json format.

    @param url:
    @return:
    """
    return url, url + '?metadata'


@registration.before_app_first_request
def initialize():
    current_app.logger.debug('Setting worker config')
    set_config(current_app.config)
    current_app.logger.debug('Starting workers')
    start_workers(5)


@registration.route('/request/', methods=['POST'])
@login_required
def post_request():
    """Submit a new registration request

  Specify in the message body:
  src: url of the source file
  checksum: the file you expect the file will have.

  The function returns a URL to check the status of the request.
  The URL includes a request ID.
  """
    current_app.logger.debug('Entering post_request()')

    if flask.request.headers.get('Content-Type') == 'application/json':
        req_body = json.loads(flask.request.data)
    else:
        req_body = flask.request.form

    registration_request = \
        RegistrationRequest(src_url=req_body['src_url'],
                            status_description='Registration request created',
                            timestamp=datetime.utcnow())
    db.session.add(registration_request)
    db.session.commit()

    context = Context()
    context.request_id = registration_request.id
    context.auth = HTTPBasicAuth(request.authorization.username, request
                                 .authorization.password)
    context.src_url, context.md_url = extract_urls(req_body['src_url'])

    current_app.logger.debug('Adding task %s ' % context)
    db.session.close()
    add_task(context)

    if request_wants(ContentTypes.json):
        return flask.jsonify(request_id=registration_request.id), 201
    else:
        return flask.render_template(
            'requestcreated.html',
            scratch=current_app.config.get('SCRATCH_SPACE', None),
            reg=registration_request), 201


@registration.route('/request/<request_id>', methods=['GET'])
@login_required
def get_request(request_id):
    """Poll the status of a request by ID."""
    r = RegistrationRequest.query.get(request_id)

    #TODO: json error?
    if r is None:
        return abort(404)

    if request_wants(ContentTypes.json):
        return flask.jsonify(
            {'request': RegistrationRequestSerializer(r).data})

    return flask.render_template(
        'singleRequest.html',
        scratch=current_app.config.get('SCRATCH_SPACE', None),
        r=r)


#### /registered container ####
#jj: this is a separate component?

@registration.route('/registered/<pid_prefix>/', methods=['GET'])
@login_required
def get_pids_by_prefix(pid_prefix):
    """Search PIDs with this prefix on handle.net

    return list of PIDs
    (with links to /registered/<full_pid>) to download
    This will not work with handle.net because it does not allow to retrieve
    all handles from given prefix. EPIC api is not an option either since
    the pids are distributed among different endpoints (so none of the will
    be able to provide full list of all prefixes used in EUDAT)

    """
    return flask.render_template(
        'pids.html',
        scratch=current_app.config.get('SCRATCH_SPACE', None))


@registration.route('/registered/<pid_prefix>/<pid_suffix>', methods=['GET'])
@login_required
def get_pid_by_handle(pid_prefix, pid_suffix):
    """Retrieves a data object by PID."""

    handle_client = EpicClient(base_uri=current_app.config['HANDLE_URI'],
                               credentials=None)
    handle_record = handle_client.retrieve_handle(prefix=pid_prefix,
                                                  suffix=pid_suffix)
    if handle_record is None:
        abort(404)

    location = select_location(handle_record.get_all_locations())
    if location:
        return redirect(location)

    #remote location use-case: comes later
    return 'Requested content is currently not available\n', \
           204, {}


def select_location(location_list):
    """Selects optimal location from a given list

    This is just a place-holder for a more sophisticated functionality.
    Currently it only returns location if they are local.

    More sophisticated solutions e.g. redirection to remote based on client
    ip, could be implemented in the future.

    @param location_list: list of the possible locations
    @return: URL for redirection, or False if nothing found
    """
    for l in location_list:
        loc = is_local(l, current_app.config['RODSHOST'],
                       current_app.config['RODSPORT'],
                       current_app.config['RODSZONE'])
        if loc and loc.startswith('http'):
            return loc 
        if loc:
            return url_for('http_storage_read.get_obj', objpath=loc)

    return False


def extract_urls(url):
    """Extract data and metadata urls from cdmi url

    @param url:
    @return:
    """
    return url + '?value', url + '?metadata'


@registration.before_app_first_request
def initialize():
    current_app.logger.debug('Setting worker config')
    set_config(current_app.config)
    current_app.logger.debug('Starting workers')
    start_workers(5)
