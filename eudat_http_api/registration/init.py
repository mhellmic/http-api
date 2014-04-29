# -*- coding: utf-8 -*-

from flask import Blueprint
import flask
from flask import current_app
from flask import request
from flask import json
from flask import abort, url_for

from eudat_http_api.common import request_wants, ContentTypes
from eudat_http_api.epicclient import EpicClient
from eudat_http_api.epicclient import HTTPClient
from eudat_http_api.cdmiclient import CDMIClient

from eudat_http_api.registration.models import db
from eudat_http_api import invenioclient
from eudat_http_api import auth
from eudat_http_api.registration.registration_worker import RegistrationWorker

from models import RegistrationRequest, RegistrationRequestSerializer
from datetime import datetime
from requests.auth import HTTPBasicAuth

registration = Blueprint('registration', __name__,
                         template_folder='templates')


def get_hal_links(reg_requests, page):
    """returns links in json hal format"""
    navi = dict()
    navi['self'] = {'href': url_for('get_requests', page=page)}
    if reg_requests.has_next:
        navi['next'] = {
            'href': url_for('get_requests', page=reg_requests.next_num)}
    if reg_requests.has_prev:
        navi['prev'] = {
            'href': url_for('get_requests', page=reg_requests.prev_num)}

    return navi


@registration.route('/request/', methods=['GET'])
@auth.requires_auth
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

    return flask.render_template('requests.html', requests=reg_requests)


@registration.route('/request/', methods=['POST'])
@auth.requires_auth
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

    r = RegistrationRequest(src_url=req_body['src_url'],
                            status_description='Registration request created',
                            timestamp=datetime.utcnow())
    db.session.add(r)
    db.session.commit()

    httpClient = HTTPClient(current_app.config['HANDLE_URI'],
                            HTTPBasicAuth(current_app.config['HANDLE_USER'],
                                          current_app.config['HANDLE_PASS']))

    cdmiclient = CDMIClient(auth=HTTPBasicAuth(request.authorization.username,
                                               request.authorization.password))

    # FIXME: due to the fuckedup blueprints I don't know how to define the destination url, something like:
    # url_for('http_storage.put_cdmi_obj',objpath='/')
    p = RegistrationWorker(request_id=r.id,
                           epic_client=EpicClient(httpClient=httpClient),
                           logger=current_app.logger, cdmi_client=cdmiclient,
                           base_url='http://localhost:8080/tmp/')
    #we have to close it explicitly already here otherwise the request object is bound to this session
    db.session.close()
    p.start()

    if request_wants(ContentTypes.json):
        return flask.jsonify(request_id=r.id), 201
    else:
        return flask.render_template('requestcreated.html', reg=r), 201


@registration.route('/request/<request_id>', methods=['GET'])
@auth.requires_auth
def get_request(request_id):
    """Poll the status of a request by ID."""
    r = RegistrationRequest.query.get(request_id)

    #TODO: json error?
    if r is None:
        return abort(404)

    if request_wants(ContentTypes.json):
        return flask.jsonify(
            {'request': RegistrationRequestSerializer(r).data})

    return flask.render_template('singleRequest.html', r=r)


#### /registered container ####
#jj: this is a separate component?

@registration.route('/registered/<pid_prefix>/', methods=['GET'])
@auth.requires_auth
def get_pids_by_prefix():
    # search PIDs with this prefix on handle.net

    # return list of PIDs
    # (with links to /registered/<full_pid>) to download
    pass


@registration.route('/registered/<pid_prefix>/<pid_suffix>', methods=['GET'])
@auth.requires_auth
def get_pid_by_handle(pid_prefix, pid_suffix):
    """Retrieves a data object by PID."""
    pid = pid_prefix + '/' + pid_suffix

    #FIXIT: invenio should not be exposed we need an abstraction
    if 'metadata' in flask.request.args:
        invenioclient.get_metadata(pid)

    # resolve PID

    # extract link to data object

    # choose link to data object

    # return data object
    return 'nothing there, baeh!'
